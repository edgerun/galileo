import logging
import signal
import threading
import time
from multiprocessing import Queue
from queue import Full

import pymq
import requests
from galileodb.model import RequestTrace
from pymq.provider.redis import RedisEventBus

from galileo import util
from galileo.apps.app import AppClient, DefaultAppClient
from galileo.routing import ServiceRequest
from galileo.worker.api import ClientDescription, ClientConfig, ClientInfo, SetWorkloadCommand, StopWorkloadCommand, \
    WorkloadDoneEvent
from galileo.worker.context import Context
from galileo.worker.random import create_sampler

logger = logging.getLogger(__name__)


def constant(mean):
    while True:
        yield mean


def limiter(limit, gen):
    for _ in range(limit):
        yield next(gen)


def create_interarrival_generator(cmd: SetWorkloadCommand):
    if not cmd.distribution or cmd.distribution == 'constant':
        if cmd.parameters:
            gen = constant(*cmd.parameters)
        else:
            gen = constant(0)
    else:
        gen = create_sampler(cmd.distribution, cmd.parameters)

    if cmd.num:
        return limiter(cmd.num, gen)
    else:
        return gen


class RequestGenerator:
    DONE = object()

    def __init__(self, factory) -> None:
        super().__init__()
        self.factory = factory

        self._closed = False

        self._gen = None
        self._gen_lock = threading.Condition()

    def close(self):
        with self._gen_lock:
            logger.debug('closing generator %s', self)
            self._closed = True
            self._gen_lock.notify_all()

    def set_workload(self, cmd: SetWorkloadCommand):
        with self._gen_lock:
            gen = create_interarrival_generator(cmd)
            self._gen = gen
            self._gen_lock.notify_all()

    def pause(self):
        with self._gen_lock:
            self._gen = None

    def _next_interarrival(self):
        gen = self._gen
        if gen is not None:
            return next(gen)

        with self._gen_lock:
            if self._gen is None:  # set_rps may already have been called and notified has_gen
                logger.debug('generator paused %s', self)
                self._gen_lock.wait()
                if self._closed or not self._gen:
                    raise InterruptedError

            logger.debug('generator resumed %s', self)

            return next(self._gen)

    def run(self):
        logger.debug('running request generator %s', self)

        factory = self.factory

        while not self._closed:
            try:
                a = self._next_interarrival()  # may block until a generator is available
                if a > 0:
                    time.sleep(a)
            except StopIteration:
                with self._gen_lock:
                    self._gen = None
                yield RequestGenerator.DONE
                continue
            except InterruptedError:
                break

            yield factory()


class AppClientRequestFactory:

    def __init__(self, service: str, client: AppClient) -> None:
        super().__init__()
        self.service = service
        self.client = client

    def create_request(self) -> ServiceRequest:
        req = self.client.next_request()
        service_request = ServiceRequest(self.service, req.endpoint, req.method, **req.kwargs)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('client %s created request %s', self.client.name, service_request.__dict__)

        return service_request

    def __call__(self, *args, **kwargs):
        return self.create_request()


class Client:

    def __init__(self, ctx: Context, trace_queue: Queue, description: ClientDescription, eventbus=None) -> None:
        super().__init__()
        self.ctx = ctx
        self.description = description
        self.client_id = description.client_id
        self.cfg = description.config
        self.traces = trace_queue
        self.eventbus = eventbus or pymq

        self.router = ctx.create_router()
        self.request_generator = RequestGenerator(self._create_request_factory())

        # used for generating request ids
        self.client_uuid = util.uuid()[-10:]
        self.request_counter = 0

        # used for statistics
        self.failed_counter = 0

        # expose methods
        self.eventbus.subscribe(self._on_set_workload_command)
        self.eventbus.subscribe(self._on_stop_workload_command)
        self.eventbus.expose(self.get_info, 'Client.get_info')

    def _create_request_id(self, _: ServiceRequest) -> str:
        self.request_counter += 1
        return self.client_uuid + ":" + str(self.request_counter)

    def get_info(self) -> ClientInfo:
        return ClientInfo(self.description, self.request_counter, self.failed_counter)

    def run(self):
        client_id = self.client_id
        traces = self.traces
        router = self.router

        rgen = self.request_generator.run()

        try:
            while True:
                logger.debug("client %s waiting for next request", client_id)
                try:
                    request = next(rgen)
                except StopIteration:
                    break

                if request is RequestGenerator.DONE:
                    self.eventbus.publish(WorkloadDoneEvent(self.client_id))
                    continue

                logger.debug('client %s processing request %s', client_id, request)
                request.client_id = client_id
                request.request_id = self._create_request_id(request)

                try:
                    request.sent = -1  # will be updated by router
                    response: requests.Response = router.request(request)
                    host = response.url.split("//")[-1].split("/")[0].split('?')[0]

                    t = RequestTrace(
                        request_id=request.request_id,
                        client=client_id,
                        service=request.service,
                        created=request.created,
                        sent=request.sent,
                        done=time.time(),
                        status=response.status_code,
                        server=host,
                        response=response.text.strip()
                    )
                except Exception as e:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.exception('error while handling request %s', request)
                    else:
                        logger.error('error while handling request %s: %s', request, e)

                    t = RequestTrace(
                        request_id=request.request_id,
                        client=client_id,
                        service=request.service,
                        created=request.created,
                        sent=request.sent,
                        done=time.time(),
                        status=-1
                    )

                if t.status < 0 or t.status >= 300:
                    self.failed_counter += 1

                try:
                    traces.put_nowait(t)
                except Full:
                    pass
        except KeyboardInterrupt:
            return
        except:
            logger.exception("error during read loop in client %s", client_id)

    def close(self):
        self.request_generator.close()
        self.eventbus.unsubscribe(self._on_set_workload_command)
        self.eventbus.unsubscribe(self._on_stop_workload_command)
        self.eventbus.unexpose('Client.get_info')

    def _on_set_workload_command(self, cmd: SetWorkloadCommand):
        if cmd.client_id != self.client_id:
            return

        self.request_generator.set_workload(cmd)

    def _on_stop_workload_command(self, cmd: StopWorkloadCommand):
        if cmd.client_id != self.client_id:
            return

        self.request_generator.pause()

    def _create_request_factory(self):
        if self.cfg.client:
            app_loader = self.ctx.create_app_loader()
            app = app_loader.load(self.cfg.client, self.cfg.parameters)
        else:
            app = DefaultAppClient(self.cfg.parameters)

        return AppClientRequestFactory(self.cfg.service, app)

    def __str__(self):
        return 'Client{client_id=%s}' % self.client_id


def single_request(cfg: ClientConfig, ctx=None, router_type=None) -> requests.Response:
    ctx = ctx or Context()

    if cfg.client:
        app_loader = ctx.create_app_loader()
        app = app_loader.load(cfg.client, cfg.parameters)
    else:
        app = DefaultAppClient(cfg.parameters)

    factory = AppClientRequestFactory(cfg.service, app)

    router = ctx.create_router(router_type)
    return router.request(factory.create_request())


def run(ctx: Context, trace_queue: Queue, description: ClientDescription):
    logger.info('starting new client process %s', description)

    bus = RedisEventBus(rds=ctx.create_redis())
    bus_thread = threading.Thread(target=bus.run)
    bus_thread.start()

    client = Client(ctx, trace_queue, description, eventbus=bus)

    def handler(signum, frame):
        logger.debug('client %s received signal %s', client.client_id, signum)
        client.close()
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    try:
        logger.info("%s starting", client)
        client.run()
    except KeyboardInterrupt:
        pass

    logger.debug('shutting down eventbus')
    bus.close()
    bus_thread.join(2)

    logger.info("%s exitting", client)

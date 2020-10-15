import logging
import signal
import threading
import time
from multiprocessing import Queue
from queue import Full

import pymq
import requests
from galileodb.model import ServiceRequestTrace
from pymq.provider.redis import RedisEventBus
from symmetry.gateway import ServiceRequest

from galileo.apps.app import AppClient, DefaultAppClient
from galileo.worker.api import ClientDescription, SetRpsCommand
from galileo.worker.context import Context

logger = logging.getLogger(__name__)


def constant(mean):
    while True:
        new = yield mean

        if new is not None:
            mean = new


generators = {
    'constant': constant
}


class RequestGenerator:

    def __init__(self, factory) -> None:
        super().__init__()
        self.factory = factory

        self._closed = False

        self.rps = (0, 'none')
        self.counter = 0
        self._gen = None
        self._gen_lock = threading.Condition()

    def close(self):
        with self._gen_lock:
            logger.debug('closing generator %s', self)
            self._closed = True
            self._gen_lock.notify_all()

    def set_rps(self, value, dist='constant', *args):
        logger.debug('setting RPS of generator: %s, %s, %s', value, dist, args)
        with self._gen_lock:
            if self._closed:
                return

            self.rps = (value, dist)

            if value is None or value <= 0:
                # pauses the request generator
                self._gen = None
                return

            if self._gen is not None and self._gen.__name__ == dist:
                self._gen.send(value)
            else:
                self._gen = generators[dist](value, *args)

            self._gen_lock.notify_all()

    def _next_interarrival(self):
        gen = self._gen  # TODO: benchmark this. doing the check on every call may slow down the request generator.
        if gen is not None:
            return 1 / next(gen)

        with self._gen_lock:
            if self._gen is None:  # set_rps may already have been called and notified has_gen
                logger.debug('generator paused %s', self)
                self._gen_lock.wait()
                if self._closed or not self._gen:
                    raise InterruptedError

            logger.debug('generator resumed %s', self)

            return 1 / next(self._gen)

    def run(self):
        logger.debug('running request generator %s', self)

        factory = self.factory

        while not self._closed:
            try:
                a = self._next_interarrival()  # may block until a generator is available
                time.sleep(a)
            except InterruptedError:
                break

            self.counter += 1
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
        self.eventbus.subscribe(self._on_set_rps_command)

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

                logger.debug('client %s processing request %s', client_id, request)
                request.client_id = client_id

                try:
                    response: requests.Response = router.request(request)
                    host = response.url.split("//")[-1].split("/")[0].split('?')[0]
                    t = ServiceRequestTrace(client_id, request.service, host, request.created, request.sent,
                                            time.time())
                except Exception as e:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.exception('error while handling request %s', request)
                    else:
                        logger.error('error while handling request %sL %s', request, e)

                    t = ServiceRequestTrace(client_id, request.service, 'none', request.created, -1, time.time())

                try:
                    traces.put_nowait(t)
                except Full:
                    pass
        except KeyboardInterrupt:
            return
        except:
            logger.exception("Error during read loop in client %s", client_id)

    def close(self):
        self.request_generator.close()

    def _on_set_rps_command(self, cmd: SetRpsCommand):
        if cmd.client_id != self.client_id:
            return

        self.request_generator.set_rps(cmd.value, dist=cmd.dist)

    def _create_request_factory(self):
        if self.cfg.client:
            app_loader = self.ctx.create_app_loader()
            app = app_loader.load(self.cfg.client, self.cfg.parameters)
        else:
            app = DefaultAppClient(self.cfg.parameters)

        return AppClientRequestFactory(self.cfg.service, app)

    def __str__(self):
        return 'Client{client_id=%s}' % self.client_id


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

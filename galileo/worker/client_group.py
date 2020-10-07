import logging
import os
import signal
import threading
import time
from multiprocessing import Queue, Process
from typing import Dict

import pymq
from pymq.provider.redis import RedisEventBus
from symmetry.gateway import ServiceRequest

import galileo.worker.client as client
from galileo import util
from galileo.apps.app import AppClient
from galileo.worker.api import ClientConfig, StartClientsCommand, SetRpsCommand, CloseClientGroupCommand
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

    def __init__(self, queue: Queue, factory) -> None:
        super().__init__()
        self.queue = queue
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

        queue = self.queue
        factory = self.factory

        while not self._closed:
            try:
                a = self._next_interarrival()  # may block until a generator is available
                time.sleep(a)
            except InterruptedError:
                break

            self.counter += 1
            queue.put(factory())


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


class ClientGroup:
    """
    A client group is a container for multiple emulated clients with the same configuration.

    Attributes
    ----------
    gid : str
        a unique string that identifies this client group

    host : str
        the worker hosting this client group

    cfg : ClientConfig
        the configuration to create the clients

    """

    def __init__(self, gid: str, cfg: ClientConfig, trace_queue: Queue, ctx: Context = None, eventbus=None) -> None:
        super().__init__()
        self.gid = gid
        self.cfg = cfg
        self.eventbus = eventbus or pymq
        self.ctx = ctx or Context()
        self.host = self.ctx.worker_name

        self.request_queue = Queue()
        self.trace_queue = trace_queue

        self._closed = False
        self._lock = threading.RLock()
        self._clients: Dict[str, Process] = dict()

        self._generator = RequestGenerator(self.request_queue, self._create_request_factory())

    def run(self):
        logger.debug('Starting ClientGroup %s in process %s', self.gid, os.getpid())
        with self._lock:
            self.eventbus.subscribe(self._on_start_clients_command)
            self.eventbus.subscribe(self._on_set_rps_command)
            self.eventbus.expose(self.info)

        self._generator.run()

        logger.debug('ClientGroup %s exitting', self.gid)

    def info(self):
        return {
            'worker': self.ctx.worker_name,
            'gid': self.gid,
            'clients': len(self._clients),
            'rps': self._generator.rps,
            'queued': self.request_queue.qsize(),
            'total': self._generator.counter
        }

    def close(self):
        logger.debug('attempting to close client group %s', self.gid)
        with self._lock:
            if self._closed:
                return
            self._closed = True

            self.eventbus.unsubscribe(self._on_start_clients_command, channel=None)
            self.eventbus.unsubscribe(self._on_set_rps_command, channel=None)

            logger.debug('closing ClientGroup %s', self.gid)
            for _ in range(len(self._clients)):
                self.request_queue.put(client.POISON)

            for process in self._clients.values():
                try:
                    process.join(2)
                except:
                    pass

            self._clients.clear()

            if self._generator:
                logger.debug('closing generator')
                self._generator.close()

    def start_new_client(self):
        logger.info("starting new client in group %s", self.gid)
        with self._lock:
            if self._closed:
                return

            client_id = self._create_client_id()
            process = Process(target=client.run, args=(client_id, self.ctx, self.request_queue, self.trace_queue))
            process.daemon = True
            process.start()
            logger.debug('started client %s', client_id)
            self._clients[client_id] = process
            return client_id

    def _on_start_clients_command(self, cmd: StartClientsCommand):
        logger.debug("%s received StartClientsCommand %s", self.gid, cmd)
        if cmd.gid != self.gid:
            return

        with self._lock:
            for _ in range(cmd.num):
                self.start_new_client()

    def _on_set_rps_command(self, cmd: SetRpsCommand):
        if cmd.gid != self.gid:
            return

        with self._lock:
            if self._closed:
                return

            logger.debug('set rps command received: %s', cmd)
            if self._generator:
                args = cmd.args or tuple()
                self._generator.set_rps(cmd.value, cmd.dist, *args)

    def _create_client_id(self):
        return 'client-{gid}-{suffix}'.format(gid=self.gid, suffix=util.uuid()[:4])

    def _create_request_factory(self):
        app_loader = self.ctx.create_app_loader()

        app = app_loader.load(self.cfg.client, self.cfg.parameters)

        return AppClientRequestFactory(self.cfg.service, app)


def run(gid: str, cfg: ClientConfig, trace_queue: Queue, ctx: Context = None):
    ctx = ctx or Context()
    logger.info('starting new client group process %s, %s', gid, cfg)

    bus = RedisEventBus(rds=ctx.create_redis())
    bus_thread = threading.Thread(target=bus.run)
    bus_thread.start()

    try:
        client_group = ClientGroup(gid, cfg, trace_queue, ctx=ctx, eventbus=bus)
    except Exception as e:
        logger.exception('Error while creating client group %s, closing client group.', gid)
        pymq.publish(CloseClientGroupCommand(gid))
        logger.debug('shutting down eventbus')
        bus.close()
        bus_thread.join(2)
        raise e

    def handler(signum, frame):
        client_group.close()

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    try:
        client_group.run()
    except KeyboardInterrupt:
        pass

    client_group.close()

    logger.debug('shutting down eventbus')
    bus.close()
    bus_thread.join(2)

    logger.debug("exitting client group %s runner" % client_group.gid)

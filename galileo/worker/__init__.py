import logging
import time
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Process, Queue
from queue import Full
from threading import Event, Lock
from typing import Iterable, Dict

import pymq
import requests
from symmetry.gateway import Router, ServiceRequest

from galileo import util
from galileo.event import RegisterEvent, RegisterCommand, UnregisterEvent, SpawnClientsCommand, InfoCommand, \
    SetRpsCommand, RuntimeMetric, CloseRuntimeCommand
from galileo.experiment.model import ServiceRequestTrace
from galileo.worker.client import ClientEmulator
from galileo.worker.context import Context
from galileo.worker.trace import TraceLogger, TraceRedisLogger, TraceDatabaseLogger, TraceFileLogger

POISON = "__POISON__"

logger = logging.getLogger(__name__)


class ExperimentClient:
    def __init__(self, client_id: str, ctx: Context, request_queue: Queue, trace_queue: Queue) -> None:
        super().__init__()
        self.router = ctx.create_router()
        self.client_id = client_id
        self.q = request_queue
        self.traces = trace_queue

    def run(self):
        client_id = self.client_id
        q = self.q
        traces = self.traces
        router = self.router

        try:
            while True:
                request: ServiceRequest = q.get()
                if request == POISON:
                    break
                request.client_id = client_id

                try:
                    response: requests.Response = router.request(request)
                    host = response.url.split("//")[-1].split("/")[0].split('?')[0]
                    t = ServiceRequestTrace(client_id, request.service, host, request.created, request.sent,
                                            time.time())
                except Exception as e:
                    logger.error('error while handling request: %s', e)
                    t = ServiceRequestTrace(client_id, request.service, 'none', request.created, -1,
                                            time.time())

                try:
                    traces.put_nowait(t)
                except Full:
                    pass

        except KeyboardInterrupt:
            return


class RequestGenerator:

    def __init__(self, queue: Queue, request_factory) -> None:
        super().__init__()
        self.queue = queue
        self.closed = False
        self._rps = None
        self._has_rps = Event()
        self.request_factory = request_factory

    @property
    def rps(self):
        return self._rps or 0

    def set_rps(self, value):
        # FIXME: potential race condition when setting too fast
        if value < 0:
            raise ValueError('cannot set negative requests per second')

        logger.info('setting rps to %s, current items in queue: %s', value, self.queue.qsize())

        if not self._rps and value > 0:
            # resetting rps to something > 0
            self._rps = value
            self._has_rps.set()
            return

        self._rps = value
        if value == 0:
            self._has_rps.clear()

    def close(self):
        self.closed = True
        self._has_rps.set()

    def _next_interarrival(self):
        if not self._rps:
            self._has_rps.wait()
            if not self._rps:
                raise InterruptedError()

            # FIXME: potential race condition when setting too fast

        # TODO: allow expovariate simulated interarrival
        return 1 / self._rps

    def run(self):
        while not self.closed:
            try:
                a = self._next_interarrival()
                time.sleep(a)
            except InterruptedError:
                break

            self.queue.put(self.request_factory())


class ServiceRuntime:
    """
    A Service Runtime holds the service clients, request queue, and request factory belonging to a specific service.
    """
    clients = set()

    def __init__(self, ctx: Context, service: ClientEmulator, trace_queue: Queue) -> None:
        super().__init__()
        self.ctx = ctx
        self.service = service
        self.request_queue = Queue(1000)
        self.trace_queue = trace_queue
        self.request_generator = RequestGenerator(self.request_queue, self.service.request_factory)
        self.host_name = ctx.worker_name

        self.closed = False

    def create_client(self):
        return ExperimentClient(self.create_client_id(), self.ctx, self.request_queue, self.trace_queue)

    def create_client_id(self):
        return "client-{host}-{service}-{id}".format(host=self.host_name, service=self.service.name, id=util.uuid()[:4])

    def start_client(self):
        if self.closed:
            raise ValueError('ServiceRuntime already closed')

        client = self.create_client()
        process = Process(target=client.run)

        self.clients.add((client, process))
        logger.info('starting client process for %s', client.client_id)
        process.start()

        return client.client_id

    def set_rps(self, val):
        logger.info('setting rps of %s to %s', self.service.name, val)
        self.request_generator.set_rps(val)

    def run(self):
        logger.info('starting service runtime %s', self.service.name)
        try:
            self.request_generator.run()
        finally:
            for i in range(len(self.clients)):
                self.request_queue.put(POISON)

            for client, process in self.clients:
                logger.debug('waiting on client process %s', client.client_id)
                process.join()

        self.clients.clear()
        logger.info('service runtime %s exitting', self.service.name)

    def close(self):
        logger.info('closing service runtime %s', self.service.name)
        self.trace_queue.put(TraceLogger.FLUSH)
        self.closed = True
        self.request_generator.close()


class ExperimentWorker:
    """
    An experiment worker manages multiple ExperimentService runtimes on a host and accepts commands via the symmetry
    event bus.

    TODO: this should support multiple runtimes per service with different parameters. (e.g., mxnet-model-server with
     the model as parameter). that is probably a deeper change.
    """

    def __init__(self, ctx: Context, services: Iterable[ClientEmulator]) -> None:
        super().__init__()
        self.ctx = ctx
        self.services = {service.name: service for service in services}
        self.host_name = ctx.worker_name

        self.trace_queue = Queue()
        self.trace_logger = ctx.create_trace_logger(self.trace_queue)
        self.trace_logger.flush_interval = 64

        self.rt_index: Dict[str, ServiceRuntime] = dict()
        self.rt_executor: ThreadPoolExecutor = None
        self._require_runtime_lock = Lock()
        self._closed = Event()

        pymq.subscribe(self._on_register_command)
        pymq.subscribe(self._on_info)
        pymq.subscribe(self._on_close_runtime, CloseRuntimeCommand.channel(self.host_name))
        pymq.subscribe(self._on_spawn_client, SpawnClientsCommand.channel(self.host_name))
        pymq.subscribe(self._on_set_rps, SetRpsCommand.channel(self.host_name))

    def run(self):
        logger.info('started with experiment services: %s', list(self.services.keys()))

        self.rt_executor = ThreadPoolExecutor()
        self._register_host()
        self.trace_logger.start()

        self._closed.wait()

    def close_runtime(self, service):
        with self._require_runtime_lock:
            if service not in self.rt_index:
                return

            rt = self.rt_index[service]
            del self.rt_index[service]

        rt.close()

    def close(self):
        try:
            with self._require_runtime_lock:
                for service in self.rt_index.values():
                    logger.info('Closing service runtime %s', service.service.name)
                    service.close()

                if self.rt_executor:
                    logger.info('Shutting down executor')
                    self.rt_executor.shutdown()

                logger.info('shutting down trace logger')
                self.trace_logger.close()
        finally:
            self._closed.set()
            self._unregister_host()

    def _require_runtime(self, service: str) -> ServiceRuntime:
        with self._require_runtime_lock:
            if service in self.rt_index:
                logger.debug('returning existing service runtime %s', service)
                return self.rt_index[service]

            if not self.rt_executor:
                raise RuntimeError('Cannot start service instance, runtime executor not started')

            if service not in self.services:
                raise ValueError('No such service %s' % service)

            logger.debug('creating new service runtime %s', service)
            experiment_service = self.services[service]
            service_runtime = ServiceRuntime(self.ctx, experiment_service, self.trace_queue)
            self.rt_executor.submit(service_runtime.run)

            self.rt_index[service] = service_runtime

            return service_runtime

    def _on_register_command(self, event: RegisterCommand):
        logger.info('received registration command')
        self._register_host()

    def _on_info(self, event: InfoCommand):
        logger.info('received info request')
        for service_name, service_rt in self.rt_index.items():
            clients = len(service_rt.clients)
            rps = service_rt.request_generator.rps if service_rt.request_generator else 0
            queue = service_rt.request_queue.qsize()

            pymq.publish(RuntimeMetric(self.host_name, service_name, 'clients', clients))
            pymq.publish(RuntimeMetric(self.host_name, service_name, 'rps', rps))
            pymq.publish(RuntimeMetric(self.host_name, service_name, 'queue', queue))

    def _on_spawn_client(self, event: SpawnClientsCommand):
        service = event.service
        num = event.num

        logger.info('received spawn client event %s %s', service, num)

        try:
            for i in range(num):
                client_id = self._require_runtime(service).start_client()
                # self.rds.publish('exp/register/client/%s' % self.host_name, client_id) # TODO: reactivate if needed
        except ValueError as e:
            logger.error('Error getting service runtime %s: %s', service, e)

    def _on_set_rps(self, event: SetRpsCommand):
        service = event.service
        val = event.rps

        try:
            self._require_runtime(service).set_rps(val)
        except ValueError as e:
            logger.error('Error getting service runtime %s: %s', service, e)

    def _on_close_runtime(self, event: CloseRuntimeCommand):
        service = event.service
        logger.info('attempting to close %s', service)
        self.close_runtime(service)

    def _register_host(self):
        logger.info('registering host %s', self.host_name)
        pymq.publish(RegisterEvent(self.host_name))

    def _unregister_host(self):
        logger.info('unregistering host %s', self.host_name)
        pymq.publish(UnregisterEvent(self.host_name))

import csv
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Process, Queue
from queue import Full, Empty
from socket import gethostname
from threading import Event, Lock
from typing import Iterable, Dict, List

import redis
import symmetry.eventbus as eventbus

from galileo import util
from galileo.event import RegisterEvent, RegisterCommand, UnregisterEvent, SpawnClientsCommand, InfoCommand, \
    SetRpsCommand, RuntimeMetric, CloseRuntimeCommand
from galileo.experiment.db import ExperimentDatabase
from galileo.experiment.db.sql import ExperimentSQLDatabase
from galileo.node.client import ExperimentService
from galileo.node.router import Router, ServiceRequestTrace

POISON = "__POISON__"

log = logging.getLogger(__name__)


class ExperimentClient:
    def __init__(self, router: Router, request_queue: Queue, trace_queue: Queue, client_id=None) -> None:
        super().__init__()
        self.router = router
        self.client_id = client_id
        self.q = request_queue
        self.traces = trace_queue
        # TODO: init router, etc...

    def run(self):
        try:
            while True:
                request = self.q.get()
                if request == POISON:
                    break
                request.client_id = self.client_id

                try:
                    self.router.request(request)
                except Exception as e:
                    log.error('error while handling request: %s', e)

                trace = request.to_trace()
                try:
                    self.traces.put_nowait(trace)
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

    def __init__(self, router: Router, service: ExperimentService, trace_queue: Queue, host_name: str = None) -> None:
        super().__init__()
        self.router = router
        self.service = service
        self.request_queue = Queue(1000)
        self.trace_queue = trace_queue
        self.request_generator = RequestGenerator(self.request_queue, self.service.request_factory)
        self.host_name = host_name or gethostname()

        self.closed = False

    def create_client(self):
        return ExperimentClient(self.router, self.request_queue, self.trace_queue, self.create_client_id())

    def create_client_id(self):
        return "client-{host}-{service}-{id}".format(host=self.host_name, service=self.service.name, id=util.uuid()[:8])

    def start_client(self):
        if self.closed:
            raise ValueError('ServiceRuntime already closed')

        client = self.create_client()
        process = Process(target=client.run)

        self.clients.add((client, process))
        log.info('starting client process for %s', client.client_id)
        process.start()

        return client.client_id

    def set_rps(self, val):
        log.info('setting rps of %s to %s', self.service.name, val)
        self.request_generator.set_rps(val)

    def run(self):
        log.info('starting service runtime %s', self.service.name)
        try:
            self.request_generator.run()
        finally:
            for i in range(len(self.clients)):
                self.request_queue.put(POISON)

            for client, process in self.clients:
                log.debug('waiting on client process %s', client.client_id)
                process.join()

        self.clients.clear()
        log.info('service runtime %s exitting', self.service.name)

    def close(self):
        log.info('closing service runtime %s', self.service.name)
        self.trace_queue.put(TraceLogger.FLUSH)
        self.closed = True
        self.request_generator.close()


class TraceLogger(Process):
    FLUSH = '__FLUSH__'

    flush_interval = 20

    def __init__(self, trace_queue: Queue) -> None:
        super().__init__()
        self.traces = trace_queue
        self.closed = False
        self.buffer = list()

    def run(self):
        try:
            return self._loop()
        finally:
            self.flush()

    def flush(self):
        if not self.buffer:
            log.debug('Buffer empty, not flushing')
            return

        if log.isEnabledFor(logging.DEBUG):
            log.debug('Flushing trace buffer')

        self._do_flush(self.buffer)

        self.buffer.clear()

    def close(self):
        self.closed = True
        self.traces.put(POISON)

    def _loop(self):
        timeout = None
        while True:
            if self.closed and timeout is None:
                log.debug('setting read timeout to 2 seconds')
                timeout = 2

            try:
                trace = self.traces.get(timeout=timeout)

                if trace == POISON:
                    log.debug('poison received, setting closed to true')
                    self.closed = True
                    continue
                elif trace == self.FLUSH:
                    log.debug('flush command received, flushing buffer')
                    self.flush()
                    continue

                self.buffer.append(trace)

                if len(self.buffer) >= self.flush_interval:
                    log.debug('flush interval reached, flushing buffer')
                    self.flush()

            except KeyboardInterrupt:
                break
            except Empty:
                log.debug('queue is empty, exitting')
                return

    def _do_flush(self, buffer: List[ServiceRequestTrace]):
        pass


class TraceRedisLogger(TraceLogger):
    key = 'exp:results:traces'

    def __init__(self, trace_queue: Queue, rds: redis.Redis) -> None:
        super().__init__(trace_queue)
        self.rds = rds

    def _do_flush(self, buffer: Iterable[ServiceRequestTrace]):
        rds = self.rds.pipeline()

        for trace in buffer:
            score = trace.created
            value = '%s,%s,%s,%.7f,%.7f,%.7f' % trace  # FIXME
            rds.zadd(self.key, {value: score})

        rds.execute()


class TraceDatabaseLogger(TraceLogger):

    def __init__(self, trace_queue: Queue, experiment_db: ExperimentDatabase) -> None:
        super().__init__(trace_queue)
        self.experiment_db = experiment_db

    def run(self):
        if isinstance(self.experiment_db, ExperimentSQLDatabase):
            # this is a terrible hack due to multiprocessing issues:
            # close() will delete the threadlocal (which is not actually accessible from the process) and create a new
            # connection. The SqlAdapter adapter design may be broken. or python multiprocessing...
            self.experiment_db.db.close()
            self.experiment_db.db.open()
        super().run()

    def _do_flush(self, buffer: Iterable[ServiceRequestTrace]):
        self.experiment_db.save_traces(list(buffer))


class TraceFileLogger(TraceLogger):

    def __init__(self, trace_queue: Queue, host_name, target_dir='/tmp/mc2/exp') -> None:
        super().__init__(trace_queue)
        self.target_dir = target_dir
        self.file_name = 'traces-%s.csv' % host_name
        self.file_path = os.path.join(self.target_dir, self.file_name)
        util.mkdirp(self.target_dir)

        self.init_file()

    def init_file(self):
        log.debug('Initializing trace file logger to log into %s', self.file_path)
        if os.path.exists(self.file_path):
            return

        log.debug('Initializing %s with header', self.file_path)
        with open(self.file_path, 'w') as fd:
            csv.writer(fd).writerow(ServiceRequestTrace._fields)

    def _do_flush(self, buffer: Iterable[ServiceRequestTrace]):
        with open(self.file_path, 'a') as fd:
            writer = csv.writer(fd)
            for row in buffer:
                writer.writerow(row)


class ExperimentHost:
    """
    An experiment host manages multiple ExperimentService runtimes on a host and accepts commands via the symmetry
    event bus.
    """

    def __init__(self, rds: redis.Redis, services: Iterable[ExperimentService], router: Router, trace_logging='file',
                 host_name=None, experiment_db: ExperimentDatabase = None) -> None:
        super().__init__()
        self.rds = rds
        self.experiment_db = experiment_db
        self.services = {service.name: service for service in services}
        self.router = router
        self.host_name = host_name or gethostname()

        self.trace_queue = Queue()
        self.trace_logger = self._create_trace_logger(trace_logging)

        self.rt_index: Dict[str, ServiceRuntime] = dict()
        self.rt_executor: ThreadPoolExecutor = None
        self._require_runtime_lock = Lock()
        self._closed = Event()

        eventbus.listener(self._on_register_command)
        eventbus.listener(self._on_info)
        eventbus.listener(self._on_close_runtime, CloseRuntimeCommand.channel(self.host_name))
        eventbus.listener(self._on_spawn_client, SpawnClientsCommand.channel(self.host_name))
        eventbus.listener(self._on_set_rps, SetRpsCommand.channel(self.host_name))

    def _create_trace_logger(self, trace_logging) -> TraceLogger:
        log.debug('trace logging: %s', trace_logging)

        # careful when passing state to the TraceLogger: it's a new process
        if not trace_logging:
            return TraceLogger(self.trace_queue)
        elif trace_logging == 'file':
            return TraceFileLogger(self.trace_queue, self.host_name)
        elif trace_logging == 'redis':
            return TraceRedisLogger(self.trace_queue, rds=self.rds)
        elif trace_logging == 'mysql':
            return TraceDatabaseLogger(self.trace_queue, self.experiment_db)
        else:
            raise ValueError('Unknown trace logging type %s' % trace_logging)

    def run(self):
        log.info('started with experiment services: %s', list(self.services.keys()))

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
                    log.info('Closing service runtime %s', service.service.name)
                    service.close()

                if self.rt_executor:
                    log.info('Shutting down executor')
                    self.rt_executor.shutdown()

                log.info('shutting down trace logger')
                self.trace_logger.close()
        finally:
            self._closed.set()
            self._unregister_host()

    def _require_runtime(self, service: str) -> ServiceRuntime:
        with self._require_runtime_lock:
            if service in self.rt_index:
                log.debug('returning existing service runtime %s', service)
                return self.rt_index[service]

            if not self.rt_executor:
                raise RuntimeError('Cannot start service instance, runtime executor not started')

            if service not in self.services:
                raise ValueError('No such service %s' % service)

            log.debug('creating new service runtime %s', service)
            experiment_service = self.services[service]
            service_runtime = ServiceRuntime(self.router, experiment_service, self.trace_queue, self.host_name)
            self.rt_executor.submit(service_runtime.run)

            self.rt_index[service] = service_runtime

            return service_runtime

    def _on_register_command(self, event: RegisterCommand):
        log.info('received registration command')
        self._register_host()

    def _on_info(self, event: InfoCommand):
        log.info('received info request')
        for service_name, service_rt in self.rt_index.items():
            clients = len(service_rt.clients)
            rps = service_rt.request_generator.rps if service_rt.request_generator else 0
            queue = service_rt.request_queue.qsize()

            eventbus.publish(RuntimeMetric(self.host_name, service_name, 'clients', clients))
            eventbus.publish(RuntimeMetric(self.host_name, service_name, 'rps', rps))
            eventbus.publish(RuntimeMetric(self.host_name, service_name, 'queue', queue))

    def _on_spawn_client(self, event: SpawnClientsCommand):
        service = event.service
        num = event.num

        log.info('received spawn client event %s %s', service, num)

        try:
            for i in range(num):
                client_id = self._require_runtime(service).start_client()
                # self.rds.publish('exp/register/client/%s' % self.host_name, client_id) # TODO: reactivate if needed
        except ValueError as e:
            log.error('Error getting service runtime %s: %s', service, e)

    def _on_set_rps(self, event: SetRpsCommand):
        service = event.service
        val = event.rps

        try:
            self._require_runtime(service).set_rps(val)
        except ValueError as e:
            log.error('Error getting service runtime %s: %s', service, e)

    def _on_close_runtime(self, event: CloseRuntimeCommand):
        service = event.service
        log.info('attempting to close %s', service)
        self.close_runtime(service)

    def _register_host(self):
        log.info('registering host %s', self.host_name)
        eventbus.publish(RegisterEvent(self.host_name))

    def _unregister_host(self):
        log.info('unregistering host %s', self.host_name)
        eventbus.publish(UnregisterEvent(self.host_name))

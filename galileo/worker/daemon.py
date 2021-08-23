import logging
import multiprocessing
import threading
from typing import Dict, List

import pymq
from galileodb.trace import START, PAUSE

import galileo.worker.client as client
from galileo.controller.cluster import RedisClusterController
from galileo.worker.api import RegisterWorkerEvent, UnregisterWorkerEvent, RegisterWorkerCommand, \
    StartTracingCommand, PauseTracingCommand, CreateClientCommand, CloseClientCommand, ClientDescription, ClientConfig
from galileo.worker.context import Context

logger = logging.getLogger(__name__)


class ClientProcess(multiprocessing.Process):
    client_description: ClientDescription

    def __init__(self, ctx, trace_queue, client_description: ClientDescription) -> None:
        super().__init__(name='process-%s' % client_description.client_id,
                         target=client.run, args=(ctx, trace_queue, client_description))
        self.client_description = client_description
        self.daemon = True


class WorkerDaemon:
    """
    The worker daemon manages multiple ClientGroup processes on a host machine and exposes several interaction points
    via pymq.
    """
    name: str

    def __init__(self, ctx: Context = None, eventbus=None, ctrl=None) -> None:
        super().__init__()
        self.ctx = ctx or Context()
        self.rds = self.ctx.create_redis()
        self.eventbus = eventbus or pymq
        self.name = self.ctx.worker_name
        self.ctrl = ctrl or RedisClusterController(self.rds, self.eventbus)

        self.trace_queue = self._create_trace_queue()
        self._trace_logger = self.ctx.create_trace_logger(self.trace_queue)

        self._lock = threading.RLock()
        self._clients: Dict[str, ClientProcess] = dict()
        self._closed = threading.Event()

        self._client_id_counter = 0

    def _create_trace_queue(self):
        return multiprocessing.Queue()

    def run(self):
        self.eventbus.subscribe(self._on_create_client_command)
        self.eventbus.subscribe(self._on_close_client_command)
        self.eventbus.subscribe(self._on_register_command)
        self.eventbus.subscribe(self._on_start_tracing)
        self.eventbus.subscribe(self._on_pause_tracing)
        self.eventbus.expose(self.worker_name, 'WorkerDaemon.ping')
        self.eventbus.expose(self.create_client, 'WorkerDaemon.create_client:%s' % self.name)

        logger.debug('WorkerDaemon %s running...', self.name)
        with self._lock:
            self._trace_logger.start()
            self._register_worker()

        try:
            self._closed.wait()
        finally:
            self._unregister_worker()
            logger.debug('WorkerDaemon %s exitting', self.name)

    def worker_name(self):
        return self.name

    def create_client(self, cmd: CreateClientCommand) -> List[ClientDescription]:
        if cmd.host != self.name:
            logger.debug('ignoring CreateClientCommand sent to %s', cmd.host)
            return []

        # TODO: validate config

        logger.info('creating client %s', cmd)

        if not cmd.num:
            return []

        result = []
        for i in range(cmd.num):
            client_id = self._create_client_id(cmd.config)
            description = ClientDescription(client_id, worker=self.name, config=cmd.config)
            logger.info('creating client %s', description)
            result.append(description)

        for d in result:
            self._clients[d.client_id] = self._start_client_process(d)

        for d in result:
            self.ctrl.register_client(d)

        return result

    def _start_client_process(self, description: ClientDescription) -> ClientProcess:
        cid = description.client_id

        if cid in self._clients:
            raise ValueError('process for client %s already registered' % cid)

        process = ClientProcess(self.ctx, self.trace_queue, description)
        logger.info('starting client process %s', process)
        process.start()
        return process

    def close(self):
        with self._lock:
            logger.debug('closing clients')
            self.close_clients()

            logger.debug("closing trace logger")
            self._trace_logger.close()
            self._trace_logger.join(timeout=3)
            self._trace_logger.terminate()
            self._trace_logger.join(timeout=2)

            logger.debug("triggering exit of control loop")
            self._closed.set()

    def close_clients(self):
        for client_id in list(self._clients.keys()):
            self.close_client(client_id)

    def close_client(self, client_id):
        if client_id not in self._clients:
            return

        # TODO: need to lock around _clients
        logger.info('closing client %s', client_id)
        process = self._clients[client_id]
        del self._clients[client_id]

        self.ctrl.unregister_client(client_id)

        process.terminate()
        logger.debug('waiting on client process %s', process.name)
        process.join(3)
        logger.debug('terminated %s', process.name)

    def _register_worker(self):
        logger.info('registering name %s', self.name)
        items = self.ctx.items()
        self.ctrl.register_worker(self.name, items)
        self.eventbus.publish(RegisterWorkerEvent(self.name))

    def _unregister_worker(self):
        logger.info('unregistering name %s', self.name)
        self.ctrl.unregister_worker(self.name)
        self.eventbus.publish(UnregisterWorkerEvent(self.name))

    def _on_create_client_command(self, command: CreateClientCommand):
        if command.host != self.name:
            logger.debug('ignoring CreateClientCommand sent to %s', command.host)
            return

        logger.info('creating client %s', command)

        # TODO

    def _on_close_client_command(self, command: CloseClientCommand):
        client_id = command.client_id

        if client_id not in self._clients:
            return

        self.close_client(client_id)

    def _on_register_command(self, _: RegisterWorkerCommand):
        logger.info('received registration command')
        self._register_worker()

    def _on_start_tracing(self, _: StartTracingCommand):
        logger.info(f'received start tracing command, tracing is activated')
        self.trace_queue.put(START)

    def _on_pause_tracing(self, _: PauseTracingCommand):
        logger.info(f'received pause tracing command, tracing is deactivated')
        self.trace_queue.put(PAUSE)

    def _create_client_id(self, config: ClientConfig):
        cnt = self._client_id_counter
        self._client_id_counter += 1
        return f'{self.name}:{config.service}:{cnt}'

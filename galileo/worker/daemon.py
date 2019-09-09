import logging
import multiprocessing
import threading
from typing import Dict

import pymq

import galileo.worker.client_group as client_group
from galileo.worker.api import CreateClientGroupCommand, CloseClientGroupCommand, ClientConfig, RegisterWorkerEvent, \
    UnregisterWorkerEvent, RegisterWorkerCommand
from galileo.worker.context import Context

logger = logging.getLogger(__name__)


class WorkerDaemon:
    """
    The worker daemon manages multiple ClientGroup processes on a host machine and exposes several interaction points
    via pymq.
    """
    name: str

    def __init__(self, ctx: Context = None, eventbus=None) -> None:
        super().__init__()
        self.ctx = ctx or Context()
        self.eventbus = eventbus or pymq
        self.name = self.ctx.worker_name

        self.trace_queue = multiprocessing.Queue()
        self._trace_logger = self.ctx.create_trace_logger(self.trace_queue)

        self._lock = threading.RLock()
        self._client_groups: Dict[str, multiprocessing.Process] = dict()
        self._closed = threading.Event()

    def run(self):
        self.eventbus.subscribe(self._on_close_client_group_command)
        self.eventbus.subscribe(self._on_create_client_group_command)
        self.eventbus.subscribe(self._on_register_command)
        self.eventbus.expose(self.ping)

        logger.debug('WorkerDaemon %s running...', self.name)
        with self._lock:
            self._trace_logger.start()
            self._register_worker()

        try:
            self._closed.wait()
        finally:
            self._unregister_worker()
            logger.debug('WorkerDaemon %s exitting', self.name)

    def ping(self):
        return self.name

    def create_client_group(self, gid, cfg: ClientConfig):
        with self._lock:
            if gid in self._client_groups:
                raise ValueError('Client group %s already exists' % gid)

            process = multiprocessing.Process(
                name='client-group-%s' % gid,
                target=client_group.run,
                args=(gid, cfg, self.trace_queue, self.ctx)
            )
            self._client_groups[gid] = process
            process.start()
            logger.debug("created and started ClientGroup %s in pid %s", gid, process.pid)

    def close_client_group(self, gid):
        with self._lock:
            if gid in self._client_groups:
                self._terminate_client_group(gid)

    def close(self):
        with self._lock:
            gids = list(self._client_groups.keys())
            for gid in gids:
                self._terminate_client_group(gid)

            logger.debug("closing trace logger")
            self._trace_logger.close()
            self._trace_logger.join(timeout=5)

            logger.debug("triggering exit of control loop")
            self._closed.set()

    def _create_client_group_id(self, command: CreateClientGroupCommand):
        """
        Creates a unique ID for the client group to be created. In an ideal world, this would be randomly generated, but
        instead we have to rely on characteristics of the client group to make it statically addressable by scripts.

        :param command: the command to create the client group
        :return: a string identifier
        """
        return f"{self.name}:{command.cfg.service}:{command.cfg.client}"

    def _terminate_client_group(self, gid, timeout=None):
        process = self._client_groups[gid]

        if not process.is_alive():
            return

        logger.debug("terminating client group process %s", process.name)
        process.terminate()

        logger.debug("waiting for process %s to terminate", process.name)
        process.join(timeout=timeout)

        del self._client_groups[gid]

    def _register_worker(self):
        logger.info('registering name %s', self.name)
        pymq.publish(RegisterWorkerEvent(self.name))

    def _unregister_worker(self):
        logger.info('unregistering name %s', self.name)
        pymq.publish(UnregisterWorkerEvent(self.name))

    def _on_create_client_group_command(self, command: CreateClientGroupCommand):
        if command.host != self.name:
            logger.debug('ignoring create client group command sent to %s' % command.host)
            return

        gid = command.gid if command.gid else self._create_client_group_id(command)
        logger.debug('creating client group with gid = %s', gid)
        self.create_client_group(gid, command.cfg)
        return gid

    def _on_close_client_group_command(self, command: CloseClientGroupCommand):
        self.close_client_group(command.gid)

    def _on_register_command(self, _: RegisterWorkerCommand):
        logger.info('received registration command')
        self._register_worker()

import logging
import logging
import math
import re
import sre_constants
from concurrent.futures.thread import ThreadPoolExecutor
from typing import List

import pymq
import redis
from pymq.provider.redis import RedisQueue
from redis import WatchError
from symmetry.common.shell import Shell, parsed, ArgumentError, print_tabular

from galileo.experiment.model import Experiment, ExperimentConfiguration, QueuedExperiment
from galileo.util import poll
from galileo.worker.api import CreateClientGroupCommand, CloseClientGroupCommand, ClientConfig, RegisterWorkerEvent, \
    UnregisterWorkerEvent, RegisterWorkerCommand, SetRpsCommand, StartClientsCommand, StopClientsCommand, \
    StartTracingCommand, PauseTracingCommand
from galileo.worker.client_group import ClientGroup
from galileo.worker.daemon import WorkerDaemon

logger = logging.getLogger(__name__)


class ExperimentQueue:
    queue: RedisQueue

    def __init__(self, queue) -> None:
        super().__init__()
        if not isinstance(queue, RedisQueue):
            raise ValueError

        self.queue = queue

    def __getattr__(self, item):
        if hasattr(self.queue, item):
            return getattr(self.queue, item)
        raise AttributeError

    def remove(self, experiment_id, retries=3):
        queue = self.queue
        key = queue._key
        rds = queue._rds

        for i in range(retries):
            try:
                with rds.pipeline() as pipe:
                    pipe.watch(key)
                    workloads = pipe.lrange(key, 0, -1)
                    pipe.multi()
                    index = -1
                    for idx, entry in enumerate(workloads):
                        item: QueuedExperiment = queue._deserialize(entry)
                        if item.experiment.id == experiment_id:
                            index = idx
                            break

                    if index == -1:
                        return False

                    pipe.lset(key, index, 'DELETE')
                    pipe.lrem(key, 1, 'DELETE')
                    pipe.execute()
                    return True
            except WatchError:
                logger.warning('WatchError cancelling experiment with id %s (try %d)', experiment_id, i)
                continue

        raise CancelError


class ExperimentController:
    # TODO: register client group in redis to avoid expensive RPC calls to all workers every time

    queue_key = 'galileo:experiments:queue'
    worker_key = 'galileo:workers'

    def __init__(self, rds: redis.Redis = None) -> None:
        super().__init__()
        self.rds = rds or redis.Redis(decode_responses=True)
        self.pubsub = None

        pymq.subscribe(self._on_register_worker)
        pymq.subscribe(self._on_unregister_worker)
        self.experiment_queue = ExperimentQueue(pymq.queue(self.queue_key))

    def queue(self, config: ExperimentConfiguration, exp: Experiment = None):
        """
        Queues an experiment for the experiment daemon to load.
        :param config: experiment configuration
        :param exp: the experiment metadata (optional, as all parameters could be generated)
        :return:
        """
        if not self.list_workers():
            raise ValueError('No workers to execute the experiment on')

        element = QueuedExperiment(exp, config)
        logger.debug('queuing experiment data: %s', element)
        self.experiment_queue.put(element)

    def cancel(self, exp_id: str) -> bool:
        return self.experiment_queue.remove(exp_id)

    def discover(self):
        pymq.publish(RegisterWorkerCommand())

    def ping(self):
        return pymq.stub(WorkerDaemon.ping, multi=True, timeout=2)()

    def client_group_info(self):
        return pymq.stub(ClientGroup.info, multi=True, timeout=2)()

    def list_workers(self, pattern: str = ''):
        workers = self.rds.smembers(self.worker_key)

        if not pattern:
            return workers

        try:
            return [worker for worker in workers if re.search('^%s$' % pattern, worker)]
        except sre_constants.error as e:
            raise ValueError('Invalid pattern %s: %s' % (pattern, e))

    def list_hosts(self, pattern: str = ''):
        return self.list_workers(pattern)

    def spawn_client(self, worker, service, num, client=None):
        client = client or service
        gid = f'{worker}:{service}:{client}'

        def gid_exists():
            return gid in [info['gid'] for info in self.client_group_info()]

        if not gid_exists():
            self.create_client_group(worker, ClientConfig(service, client), gid=gid)
            # wait for the client group to appear
            poll(gid_exists, timeout=2)

        # start client process
        self.start_client(gid, num)
        return gid

    def set_rps(self, worker, service, rps, client=None):
        client = client or service
        return pymq.publish(SetRpsCommand(f'{worker}:{service}:{client}', rps))

    def close_runtime(self, worker, service, client=None):
        client = client or service
        self.close_client_group(f'{worker}:{service}:{client}')

    def create_client_group(self, worker, cfg: ClientConfig, gid=None):
        pymq.publish(CreateClientGroupCommand(worker, cfg, gid))

    def start_client(self, gid, num=1):
        pymq.publish(StartClientsCommand(gid, num))

    def stop_client(self, gid, num=1):
        pymq.publish(StopClientsCommand(gid, num))

    def close_client_group(self, gid):
        pymq.publish(CloseClientGroupCommand(gid))

    def _on_register_worker(self, event: RegisterWorkerEvent):
        self.rds.sadd('galileo:workers', event.name)

    def _on_unregister_worker(self, event: UnregisterWorkerEvent):
        self.rds.srem('galileo:workers', event.name)
        self.rds.delete('galileo:clients:%s' % event.name)

    def set_trace_logging(self, status: str):
        if status == 'on':
            pymq.publish(StartTracingCommand())

        if status == 'off':
            pymq.publish(PauseTracingCommand())


class ExperimentShell(Shell):
    intro = 'Welcome to the interactive galileo Shell.'
    prompt = 'galileo> '

    controller = None

    def __init__(self, controller: ExperimentController, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.controller = controller

    def preloop(self):
        if not self.controller:
            raise RuntimeError('Controller not set')

        self.controller.discover()

    @parsed
    def do_workers(self, pattern: str = ''):
        try:
            for worker in self.controller.list_workers(pattern):
                self.println(worker)
        except ValueError as e:
            raise ArgumentError(e)

    @parsed
    def do_client_groups(self, worker: str):
        infos = self.controller.client_group_info()

        if worker:
            for info in infos:
                if info['worker'] == worker:
                    self.println(info['gid'])
        else:
            for worker in self.controller.list_workers():
                self.println('worker:', worker)
                for info in infos:
                    if info['worker'] == worker:
                        self.println('  ', info['gid'])

    @parsed
    def do_info(self):
        print_tabular(self.controller.client_group_info(), printer=self.println)

    @parsed
    def do_discover(self):
        self.controller.discover()

    @parsed
    def do_logging(self, status: str):
        """
        Turn trace logging of workers on/off.

        :param status: 'on' or 'off'
        """
        if status == 'on' or status == 'off':
            self.controller.set_trace_logging(status)
        else:
            self.println("Wrong input, must be 'on' or 'off'.")

    @parsed
    def do_ping(self):
        result = self.controller.ping()
        for worker in result:
            self.println(worker)

    @parsed
    def do_spawn(self, worker_pattern, service, num: int = 1, client: str = ''):
        """
        Spawn a new client for the given service on the given worker.

        :param worker_pattern: the worker name or pattern (e.g., 'pico1' or 'pico[0-9]')
        :param service: the service name
        :param num: the number of clients
        :param client: the client app name (optional, if not given will use service name)
        """

        def spawn_client(worker):
            try:
                gid = self.controller.spawn_client(worker, service, num, client if client else None)
                self.println('%s: OK (%s)' % (worker, gid))
                return gid
            except Exception as ex:
                self.println('%s: ERROR (%s)' % (worker, str(ex)))
                return None

        try:
            with ThreadPoolExecutor(max_workers=8) as executor:
                workers = self.controller.list_workers(worker_pattern)
                self.println('spawning clients on %d workers' % len(workers))
                for _ in executor.map(spawn_client, workers):
                    pass  # iterator blocks until all are commands have returned

        except ValueError as e:
            raise ArgumentError(e)

    @parsed
    def do_rps(self, worker_pattern, service, rps: float, client: str = ''):
        try:
            for worker in self.controller.list_workers(worker_pattern):
                self.controller.set_rps(worker, service, rps, client if client else None)
        except ValueError as e:
            raise ArgumentError(e)

    @parsed
    def do_close(self, worker_pattern, service, client: str = ''):
        try:
            for worker in self.controller.list_workers(worker_pattern):
                self.controller.close_runtime(worker, service, client if client else None)
        except ValueError as e:
            raise ArgumentError(e)


def create_instructions(cfg: ExperimentConfiguration, workers: List[str]) -> List[str]:
    commands = list()

    if cfg.interval <= 0:
        raise ValueError('interval has to be a non-zero positive integer')

    for workload in cfg.workloads:
        for worker in workers:
            if workload.client:
                commands.append(f'spawn {worker} {workload.service} {workload.clients_per_host} {workload.client}')
            else:
                commands.append(f'spawn {worker} {workload.service} {workload.clients_per_host}')

    ticks = int(math.ceil(cfg.duration / cfg.interval))

    for t in range(ticks):
        for workload in cfg.workloads:
            service_rps = workload.ticks[t]
            worker_rps = [0] * len(workers)

            # distribute service rps across workers
            for i in range(service_rps):
                worker_rps[i % len(workers)] += 1

            for i in range(len(workers)):
                if workload.client:
                    commands.append(f'rps {workers[i]} {workload.service} {worker_rps[i]} {workload.client}')
                else:
                    commands.append(f'rps {workers[i]} {workload.service} {worker_rps[i]}')

        commands.append('sleep %d' % cfg.interval)

    for workload in cfg.workloads:
        for worker in workers:
            if workload.client:
                commands.append(f'rps {worker} {workload.service} 0 {workload.client}')
            else:
                commands.append(f'rps {worker} {workload.service} 0')
    for workload in cfg.workloads:
        for worker in workers:
            if workload.client:
                commands.append(f'close {worker} {workload.service} {workload.client}')
            else:
                commands.append(f'close {worker} {workload.service}')

    return commands


class CancelError(Exception):
    pass

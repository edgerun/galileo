import logging
import re
import sre_constants

import pymq
import redis
from galileodb import Experiment
from galileodb.model import QueuedExperiment, ExperimentConfiguration
from pymq.provider.redis import RedisQueue
from redis import WatchError

from galileo.util import poll
from galileo.worker.api import RegisterWorkerCommand, ClientConfig, SetRpsCommand, CreateClientGroupCommand, \
    StartClientsCommand, StopClientsCommand, CloseClientGroupCommand, RegisterWorkerEvent, UnregisterWorkerEvent, \
    StartTracingCommand, PauseTracingCommand
from galileo.worker.client_group import ClientGroup
from galileo.worker.daemon import WorkerDaemon

logger = logging.getLogger(__name__)


class CancelError(Exception):
    pass


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

    def spawn_client(self, worker, service, num, client=None, parameters: dict = None):
        client = client or service
        gid = f'{worker}:{service}:{client}'

        def gid_exists():
            return gid in [info['gid'] for info in self.client_group_info()]

        if not gid_exists():
            self.create_client_group(worker, ClientConfig(service, client, parameters), gid=gid)
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

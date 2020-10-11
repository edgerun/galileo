import logging

import pymq
import redis
from galileodb import Experiment
from galileodb.model import QueuedExperiment, ExperimentConfiguration
from pymq.provider.redis import RedisQueue
from redis import WatchError

from galileo.controller import RedisClusterController

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
    queue_key = 'galileo:experiments:queue'

    def __init__(self, rds: redis.Redis = None, eventbus=None) -> None:
        super().__init__()
        self.rds = rds or redis.Redis(decode_responses=True)
        self.eventbus = eventbus or pymq
        self.cluster = RedisClusterController(self.rds, eventbus=self.eventbus)
        self.experiment_queue = ExperimentQueue(self.eventbus.queue(self.queue_key))

    def queue(self, config: ExperimentConfiguration, exp: Experiment = None):
        """
        Queues an experiment for the experiment daemon to load.
        :param config: experiment configuration
        :param exp: the experiment metadata (optional, as all parameters could be generated)
        :return:
        """
        if not self.cluster.list_workers():
            raise ValueError('No workers to execute the experiment on')

        element = QueuedExperiment(exp, config)
        logger.debug('queuing experiment data: %s', element)
        self.experiment_queue.put(element)

    def cancel(self, exp_id: str) -> bool:
        return self.experiment_queue.remove(exp_id)

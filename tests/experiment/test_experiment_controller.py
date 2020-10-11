import logging
import unittest

import pymq
from galileodb.model import ExperimentConfiguration, WorkloadConfiguration, QueuedExperiment, Experiment
from pymq.provider.redis import RedisConfig

from galileo.controller import ClusterController, ExperimentController, RedisClusterController
from tests.testutils import RedisResource

logging.basicConfig(level=logging.DEBUG)


class TestExperimentDaemon(unittest.TestCase):
    redis_resource: RedisResource = RedisResource()
    ectl: ExperimentController
    cctl: ClusterController

    def setUp(self) -> None:
        self.rds = self.init_rds()
        pymq.init(RedisConfig(self.rds))
        self.ectl = ExperimentController(self.rds)
        self.cctl = RedisClusterController(self.rds)
        self.rds.delete(RedisClusterController.worker_key, ExperimentController.queue_key)

    def tearDown(self) -> None:
        self.rds.delete(RedisClusterController.worker_key, ExperimentController.queue_key)
        pymq.shutdown()
        self.redis_resource.tearDown()

    def test_queue(self):
        self.cctl.register_worker('host1')

        exp = Experiment(name='my-experiment', creator='unittest')
        config = ExperimentConfiguration(2, 1, [WorkloadConfiguration('aservice', [1, 2], 2, 'constant')])
        self.ectl.queue(config, exp)

        queue = pymq.queue(ExperimentController.queue_key)

        self.assertEqual(1, queue.qsize())
        self.assertEqual(1, self.ectl.experiment_queue.qsize())

        queued_experiment: QueuedExperiment = queue.get()
        self.assertEqual(config, queued_experiment.configuration)
        self.assertEqual('my-experiment', queued_experiment.experiment.name)
        self.assertEqual('unittest', queued_experiment.experiment.creator)

    def test_cancel(self):
        self.cctl.register_worker('host1')

        exp_id = 'abcd'
        exp = Experiment(id=exp_id, name='my-experiment', creator='unittest')
        config = ExperimentConfiguration(2, 1, [])
        self.ectl.queue(config, exp)

        exp = Experiment(id='abcdef', name='my-experiment-2', creator='unittest')
        config = ExperimentConfiguration(2, 1, [])
        self.ectl.queue(config, exp)

        self.assertEqual(2, self.ectl.experiment_queue.qsize())
        cancelled = self.ectl.cancel(exp_id)
        self.assertTrue(cancelled)
        self.assertEqual(1, self.ectl.experiment_queue.qsize())

        queued = self.ectl.experiment_queue.get()
        self.assertEqual('abcdef', queued.experiment.id, 'expected to find experiment that was not cancelled')

    def init_rds(self):
        self.redis_resource.setUp()
        return self.redis_resource.rds


if __name__ == '__main__':
    unittest.main()

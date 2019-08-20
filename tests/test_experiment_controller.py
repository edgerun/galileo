import json
import logging
import unittest

import redis
import pymq
from pymq.provider.redis import RedisConfig

from galileo.controller import ExperimentController
from galileo.experiment.model import ExperimentConfiguration, WorkloadConfiguration

logging.basicConfig(level=logging.DEBUG)


class TestExperimentDaemon(unittest.TestCase):
    rds: redis.Redis
    ectl: ExperimentController

    def setUp(self) -> None:
        self.rds = redis.Redis(decode_responses=True)
        pymq.init(RedisConfig(self.rds))
        self.ectl = ExperimentController(self.rds)
        self.rds.delete(ExperimentController.worker_key, ExperimentController.queue_key)

    def tearDown(self) -> None:
        self.rds.delete(ExperimentController.worker_key, ExperimentController.queue_key)
        pymq.shutdown()

    def test_submit(self):
        self.rds.sadd(ExperimentController.worker_key, 'host1')

        load = ExperimentConfiguration(2, 1, [WorkloadConfiguration('aservice', [1, 2], 2, 'constant')])
        self.ectl.queue(load)

        message = self.rds.lpop(ExperimentController.queue_key)
        expected = {
            'instructions': 'spawn host1 aservice 2\nrps host1 aservice 1\nsleep 1\nrps host1 aservice 2\nsleep 1\nrps host1 aservice 0\nclose host1 aservice'
        }
        actual = json.loads(message)
        self.assertEqual(expected, actual)

    def test_cancel(self):
        exp_id = 'abcd'
        exp = {
            'id': exp_id,
            'instructions': 'spawn host1 aservice 2\nrps host1 aservice 1\nsleep 1\nrps host1 aservice 2\nsleep 1\nrps host1 aservice 0\nclose host1 aservice'
        }
        self.rds.lpush(ExperimentController.queue_key, json.dumps(exp))

        cancelled = self.ectl.cancel(exp_id)
        self.assertTrue(cancelled)
        queued = self.rds.lrange(ExperimentController.queue_key, 0, -1)
        self.assertEqual(len(queued), 0)
        pass


if __name__ == '__main__':
    unittest.main()

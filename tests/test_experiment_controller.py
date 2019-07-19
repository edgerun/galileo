import json
import logging
import unittest

import redis
from symmetry import eventbus
from symmetry.eventbus.redis import RedisConfig

from galileo.controller import ExperimentController
from galileo.experiment.model import ExperimentConfiguration, WorkloadConfiguration

logging.basicConfig(level=logging.DEBUG)


class TestExperimentDaemon(unittest.TestCase):
    rds: redis.Redis
    ectl: ExperimentController

    def setUp(self) -> None:
        self.rds = redis.Redis(decode_responses=True)
        eventbus.init(RedisConfig(self.rds))
        self.ectl = ExperimentController(self.rds)
        self.rds.delete('exp:hosts', ExperimentController.queue_key)

    def tearDown(self) -> None:
        self.rds.delete('exp:hosts', ExperimentController.queue_key)
        eventbus.shutdown()

    def test_submit(self):
        self.rds.sadd('exp:hosts', 'host1')

        load = ExperimentConfiguration(2, 1, [WorkloadConfiguration('aservice', [1, 2], 2)])
        self.ectl.queue(load)

        message = self.rds.lpop(ExperimentController.queue_key)
        expected = {
            'instructions': 'spawn host1 aservice 2\nrps host1 aservice 1\nsleep 1\nrps host1 aservice 2\nsleep 1\nrps host1 aservice 0\nclose host1 aservice'
        }
        actual = json.loads(message)
        self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()

import json
import logging
import threading
import time
import unittest

import pymq
from pymq.provider.redis import RedisConfig

from galileo.controller import ExperimentController
from galileo.experiment.db.sql import ExperimentSQLDatabase
from galileo.experiment.experimentd import ExperimentDaemon
from galileo.experiment.service.experiment import SimpleExperimentService
from galileo.experiment.service.instructions import SimpleInstructionService
from galileo.experiment.service.telemetry import ExperimentTelemetryRecorder
from tests.testutils import RedisResource, SqliteResource

logging.basicConfig(level=logging.DEBUG)


class TestExperimentDaemon(unittest.TestCase):
    exp_db: ExperimentSQLDatabase
    redis_resource: RedisResource = RedisResource()

    def setUp(self) -> None:
        self.rds = self.init_rds()
        self.exp_db = self.init_db()
        pymq.init(RedisConfig(self.rds))

        self.recorder_factory = lambda exp_id: ExperimentTelemetryRecorder(self.rds, self.exp_db, exp_id)
        self.exp_ctrl = ExperimentController(self.rds)
        self.exp_service = SimpleExperimentService(self.exp_db)
        self.ins_service = SimpleInstructionService(self.exp_db)

    def tearDown(self) -> None:
        pymq.shutdown()
        self.redis_resource.tearDown()
        self.db_resource.tearDown()

    def test_integration(self):
        daemon = ExperimentDaemon(self.rds, self.recorder_factory, self.exp_ctrl, self.exp_service, self.ins_service)

        def inject_experiment():
            message = {
                'id': 'experiment_id',
                'creator': 'unittest',
                'instructions': 'sleep 1\necho "foo"'
            }
            time.sleep(0.5)

            self.rds.lpush(ExperimentController.queue_key, json.dumps(message))
            time.sleep(0.5)
            daemon.cancel()

        threading.Thread(target=inject_experiment).start()
        daemon.run()

        exp = self.exp_service.find('experiment_id')
        self.assertIsNotNone(exp)
        self.assertEqual('FINISHED', exp.status)
        self.assertEqual('experiment_id', exp.id)
        self.assertEqual('experiment_id', exp.name)

        ins = self.exp_db.get_instructions(exp.id)
        self.assertIsNotNone(ins)
        self.assertEqual('sleep 1\necho "foo"', ins.instructions)
        # TODO: extend asserts, this doesn't really test anything

    def init_rds(self):
        self.redis_resource.setUp()
        return self.redis_resource.rds

    def init_db(self):
        self.db_resource = SqliteResource()
        self.db_resource.setUp()
        return self.db_resource.db


if __name__ == '__main__':
    unittest.main()

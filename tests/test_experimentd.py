import json
import logging
import os
import tempfile
import threading
import time
import unittest

import redis
from symmetry import eventbus
from symmetry.eventbus.redis import RedisConfig

from galileo.controller import ExperimentController
from galileo.experiment.db.sql import ExperimentSQLDatabase
from galileo.experiment.db.sql.sqlite import SqliteAdapter
from galileo.experiment.experimentd import ExperimentDaemon
from galileo.experiment.service.experiment import SimpleExperimentService
from galileo.experiment.service.instructions import SimpleInstructionService
from galileo.experiment.service.telemetry import ExperimentTelemetryRecorder

logging.basicConfig(level=logging.DEBUG)


class TestExperimentDaemon(unittest.TestCase):
    db_file = None
    exp_db: ExperimentSQLDatabase
    rds: redis.Redis

    def setUp(self) -> None:
        self.rds = redis.Redis(decode_responses=True)
        eventbus.init(RedisConfig(self.rds))

        self.db_file = tempfile.mktemp('.sqlite', 'galileo_test_')
        self.exp_db = ExperimentSQLDatabase(SqliteAdapter(self.db_file))
        self.exp_db.open()
        self.recorder_factory = lambda exp_id: ExperimentTelemetryRecorder(self.rds, self.exp_db, exp_id)
        self.exp_ctrl = ExperimentController(self.rds)
        self.exp_service = SimpleExperimentService(self.exp_db)
        self.ins_service = SimpleInstructionService(self.exp_db)

    def tearDown(self) -> None:
        self.exp_db.close()
        os.remove(self.db_file)
        eventbus.shutdown()

    def test_integration(self):
        daemon = ExperimentDaemon(self.rds, self.recorder_factory, self.exp_ctrl, self.exp_service, self.ins_service)

        def inject_experiment():
            message = {
                'id': 'experiment_id',
                'creator': 'unittest',
                'instructions': 'sleep 1\necho "foo"'
            }
            time.sleep(0.5)

            self.rds.lpush(ExperimentDaemon.queue_key, json.dumps(message))
            time.sleep(0.5)
            daemon.cancel()
            time.sleep(0.5)
            self.rds.lpush(ExperimentDaemon.queue_key, '')

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


if __name__ == '__main__':
    unittest.main()

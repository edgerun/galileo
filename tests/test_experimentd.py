import logging
import threading
import unittest
from unittest.mock import patch

import pymq
from galileodb import ExperimentDatabase
from galileodb.model import QueuedExperiment, Experiment, ExperimentConfiguration, WorkloadConfiguration
from galileodb.recorder import ExperimentTelemetryRecorder
from pymq.provider.redis import RedisConfig

from galileo.controller import ExperimentController
from galileo.experiment.experimentd import ExperimentDaemon
from galileo.experiment.service.experiment import SimpleExperimentService
from galileo.util import poll
from tests.testutils import RedisResource, SqliteResource

logging.basicConfig(level=logging.DEBUG)


class TestExperimentDaemon(unittest.TestCase):
    exp_db: ExperimentDatabase
    redis_resource: RedisResource = RedisResource()

    def setUp(self) -> None:
        self.rds = self.init_rds()
        self.exp_db = self.init_db()
        pymq.init(RedisConfig(self.rds))

        self.recorder_factory = lambda exp_id: ExperimentTelemetryRecorder(self.rds, self.exp_db, exp_id)
        self.exp_ctrl = ExperimentController(self.rds)
        self.exp_service = SimpleExperimentService(self.exp_db)

    def tearDown(self) -> None:
        pymq.shutdown()
        self.redis_resource.tearDown()
        self.db_resource.tearDown()

    @patch('galileo.experiment.experimentd.ExperimentBatchShell.run_batch')
    def test_integration(self, mocked_run_batch):
        self.rds.sadd(ExperimentController.worker_key, 'host1')  # create a worker

        daemon = ExperimentDaemon(self.rds, self.recorder_factory, self.exp_ctrl, self.exp_service)

        def inject_experiment():
            exp = Experiment('experiment_id', creator='unittest')
            cfg = ExperimentConfiguration(2, 1, [WorkloadConfiguration('aservice', [3, 5], 2, 'constant')])

            queue = pymq.queue(ExperimentController.queue_key)
            queue.put(QueuedExperiment(exp, cfg))
            try:
                poll(lambda: queue.qsize() == 0, timeout=2, interval=0.1)  # wait for the daemon to take the experiment
            finally:
                daemon.close()

        threading.Thread(target=inject_experiment).start()
        daemon.run()

        # wait for the experiment to be created
        poll(lambda: self.exp_service.exists('experiment_id'), timeout=2, interval=0.1)
        # wait for the experiment to be finished
        poll(lambda: self.exp_service.find('experiment_id').status == 'FINISHED', timeout=2, interval=0.1)

        # verify that the experiment parameters were set correctly
        exp = self.exp_service.find('experiment_id')
        self.assertIsNotNone(exp)
        self.assertEqual('FINISHED', exp.status)
        self.assertEqual('experiment_id', exp.id)
        self.assertEqual('experiment_id', exp.name)

        # verify that experiment daemon tried to run the commands
        self.assertTrue(mocked_run_batch.called, 'expected ExperimentDaemon to run commands on ExperimentShell')
        self.assertIn('spawn host1 aservice 2', mocked_run_batch.call_args[0][0])  # first call, first argument
        self.assertIn('close host1 aservice', mocked_run_batch.call_args[0][0])

    def init_rds(self):
        self.redis_resource.setUp()
        return self.redis_resource.rds

    def init_db(self):
        self.db_resource = SqliteResource()
        self.db_resource.setUp()
        return self.db_resource.db


if __name__ == '__main__':
    unittest.main()

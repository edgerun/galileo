import logging
import time
import unittest

from symmetry.api import Telemetry, NodeInfo
from symmetry.telemetry.telemd import RedisTelemetryDataPublisher

from galileo.experiment.db.sql import ExperimentSQLDatabase
from galileo.experiment.service.telemetry import ExperimentTelemetryRecorder
from tests.testutils import RedisResource, SqliteResource

logging.basicConfig(level=logging.DEBUG)


class TestExperimentTelemetryRecorder(unittest.TestCase):
    redis_resource: RedisResource = RedisResource()
    db_resource: SqliteResource = SqliteResource()

    exp_db: ExperimentSQLDatabase
    publisher: RedisTelemetryDataPublisher

    def setUp(self) -> None:
        self.redis_resource.setUp()
        self.db_resource.setUp()
        self.publisher = RedisTelemetryDataPublisher(self.redis_resource.rds)

    def tearDown(self) -> None:
        self.redis_resource.tearDown()
        self.db_resource.tearDown()

    def test_recorder_flushes_after_stop(self):
        recorder = ExperimentTelemetryRecorder(self.redis_resource.rds, self.db_resource.db, 'unittest')
        recorder.start()
        time.sleep(0.1)

        try:
            self.publisher.on_data(None, Telemetry('cpu', NodeInfo('node1', 'host1'), 1, 31))
            self.publisher.on_data(None, Telemetry('cpu', NodeInfo('node2', 'host2'), 2, 32))
        finally:
            recorder.stop()

        recorder.join()

        records = self.db_resource.sql.fetchall('SELECT * FROM `telemetry` WHERE EXP_ID = "unittest"')
        self.assertEqual(2, len(records))
        self.assertEqual(('unittest', 1.0, 'cpu', 'node1', 31.0), records[0])
        self.assertEqual(('unittest', 2.0, 'cpu', 'node2', 32.0), records[1])

    def test_publish_status_recorded_correctly(self):
        recorder = ExperimentTelemetryRecorder(self.redis_resource.rds, self.db_resource.db, 'unittest')
        recorder.start()
        time.sleep(0.1)

        try:
            self.publisher.on_data(None, Telemetry('cpu', NodeInfo('node1', 'host1'), 3, 33))
            self.publisher.on_disconnect(NodeInfo('node1', 'host1'))
            self.publisher.on_data(None, Telemetry('cpu', NodeInfo('node2', 'host2'), 4, 34))
        finally:
            recorder.stop()

        recorder.join()

        records = self.db_resource.sql.fetchall('SELECT * FROM `telemetry` WHERE EXP_ID = "unittest"')
        self.assertEqual(3, len(records))
        self.assertEqual(('unittest', 3.0, 'cpu', 'node1', 33.0), records[0])
        self.assertEqual(('unittest', 4.0, 'cpu', 'node2', 34.0), records[2])

        self.assertEqual('unittest', records[1][0])
        # we don't know the timestamp of the disconnect event
        self.assertEqual('status', records[1][2])
        self.assertEqual('node1', records[1][3])
        self.assertEqual(0, records[1][4])

    def test_publish_non_float_value_does_not_break_recorder(self):
        recorder = ExperimentTelemetryRecorder(self.redis_resource.rds, self.db_resource.db, 'unittest')
        recorder.start()
        time.sleep(0.1)

        try:
            self.publisher.on_data(None, Telemetry('cpu', NodeInfo('node1', 'host1'), 5, 35))
            self.publisher.on_data(None, Telemetry('cpu', NodeInfo('node1', 'host1'), 6, 'foo'))
            self.publisher.on_data(None, Telemetry('cpu', NodeInfo('node2', 'host2'), 7, 37))
        finally:
            recorder.stop()

        recorder.join()

        records = self.db_resource.sql.fetchall('SELECT * FROM `telemetry` WHERE EXP_ID = "unittest"')
        self.assertEqual(2, len(records))
        self.assertEqual(('unittest', 5.0, 'cpu', 'node1', 35.0), records[0])
        self.assertEqual(('unittest', 7.0, 'cpu', 'node2', 37.0), records[1])


if __name__ == '__main__':
    unittest.main()

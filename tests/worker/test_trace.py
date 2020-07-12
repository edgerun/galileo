import multiprocessing
import shutil
import threading
import unittest
from time import sleep
from unittest.mock import patch

from galileodb.model import ServiceRequestTrace
from timeout_decorator import timeout_decorator

from galileo.worker.trace import TraceLogger, POISON, TraceRedisLogger, TraceDatabaseLogger, TraceFileLogger, START, \
    PAUSE, FLUSH
from tests.testutils import RedisResource, SqliteResource, assert_poll


class AbstractTestTraceLogger(unittest.TestCase):

    def setUp(self) -> None:
        self.queue = multiprocessing.Queue()
        self.logger = TraceLogger(self.queue)
        self.logger.flush_interval = 2
        self.flush_interval = 2
        self.thread = threading.Thread(target=self.logger.run)
        self.thread.start()

    def tearDown(self) -> None:
        if not self.logger.closed:
            self.logger.close()
        self.thread.join(2)

    @patch('galileo.worker.trace.TraceLogger.flush')
    def test_flush_called(self, flush):
        self.trigger_flush()
        assert_poll(lambda: flush.called_once(), 'Flush was not called after triggering flush')

    @patch('galileo.worker.trace.TraceLogger.flush')
    def test_flush_called_after_flush_msg(self, flush):
        self.send_message(FLUSH)
        assert_poll(lambda: flush.called_once(), 'Flush was not called after triggering FLUSH')

    def test_closed_after_poison(self):
        self.send_message(POISON)
        assert_poll(lambda: self.logger.closed, 'POISON didnt close logger')

    @patch('galileo.worker.trace.TraceLogger.flush')
    def test_flushed_after_poison(self, flush):
        self.send_message(POISON)
        assert_poll(lambda: flush.called_once(), 'Flush was not called after POISON')

    def test_running_after_start(self):
        self.send_message(START)
        assert_poll(lambda: self.logger.running, 'Logger not running after START')

    def test_not_running_after_pause(self):
        self.send_message(PAUSE)
        assert_poll(lambda: not self.logger.running, 'Logger running after PAUSE')

    def trigger_flush(self):
        for i in range(self.flush_interval):
            self.queue.put(ServiceRequestTrace('client', 'service', 'host', i, 1, 1))

    def send_message(self, msg):
        self.queue.put(msg)


class AbstractTraceLoggerTestCase:

    def test_flush(self):
        self.trigger_flush()
        assert_poll(lambda: self.count_traces() == self.flush_interval, 'Logger did not write out traces')

    def test_flush_after_flush_msg(self):
        self.send_message(ServiceRequestTrace('client', 'service', 'host', 1, 1, 1))
        self.send_message(FLUSH)
        assert_poll(lambda: self.count_traces() == 1, 'Not flushed after FLUSH')

    def test_flush_after_pause(self):
        self.send_message(ServiceRequestTrace('client', 'service', 'host', 1, 1, 1))
        self.send_message(PAUSE)
        assert_poll(lambda: self.count_traces() == 1, 'Logger did not flush after PAUSE')

    def test_discarding_messages_in_paused_state(self):
        self.send_message(PAUSE)
        self.trigger_flush()
        sleep(0.5)
        self.assert_flush(0)

    def test_recording_messages_after_starting(self):
        self.send_message(PAUSE)
        self.trigger_flush()
        sleep(0.5)
        self.assert_flush(0)
        self.send_message(START)
        self.trigger_flush()
        assert_poll(lambda: self.count_traces() == self.flush_interval,
                    'Logger did not flush after setting it back to active')

    def send_message(self, msg):
        self.queue.put(msg)

    def trigger_flush(self):
        for i in range(self.flush_interval):
            self.queue.put(ServiceRequestTrace('client', 'service', 'host', i, 1, 1))

    def assert_flush(self, n: int):
        raise NotImplementedError

    def count_traces(self) -> int:
        raise NotImplementedError


class TestRedisTraceLogger(AbstractTraceLoggerTestCase, unittest.TestCase):
    redis_resource = RedisResource()

    def setUp(self) -> None:
        self.redis_resource.setUp()
        self.queue = multiprocessing.Queue()
        self.logger = TraceRedisLogger(self.queue, self.redis_resource.rds)
        self.logger.flush_interval = 2
        self.flush_interval = 2
        self.thread = threading.Thread(target=self.logger.run)
        self.thread.start()

    def tearDown(self) -> None:
        if not self.logger.closed:
            self.logger.close()
        self.thread.join(2)
        self.redis_resource.tearDown()

    @timeout_decorator.timeout(5)
    def assert_flush(self, n):
        traces = self.redis_resource.rds.zrange(self.logger.key, 0, -1)
        self.assertEqual(len(traces), n)

    @timeout_decorator.timeout(5)
    def count_traces(self) -> int:
        return self.redis_resource.rds.zcard(self.logger.key)


class TestTraceDatabaseLogger(AbstractTraceLoggerTestCase, unittest.TestCase):
    sql_resource = SqliteResource()

    def setUp(self) -> None:
        self.sql_resource.setUp()
        self.queue = multiprocessing.Queue()
        self.logger = TraceDatabaseLogger(self.queue, self.sql_resource.db)
        self.logger.flush_interval = 2
        self.flush_interval = 2
        self.thread = threading.Thread(target=self.logger.run)
        self.thread.start()

    def tearDown(self) -> None:
        if not self.logger.closed:
            self.logger.close()
        self.thread.join(2)
        self.sql_resource.tearDown()

    @timeout_decorator.timeout(5)
    def assert_flush(self, n):
        traces = self.sql_resource.sql.fetchall('SELECT * FROM `traces`')
        self.assertEqual(len(traces), n)

    @timeout_decorator.timeout(5)
    def count_traces(self) -> int:
        return len(self.sql_resource.sql.fetchall('SELECT * FROM `traces`'))


class TestTraceFileLogger(AbstractTraceLoggerTestCase, unittest.TestCase):
    target_dir = '/tmp/galileo_test'

    def setUp(self) -> None:
        self.queue = multiprocessing.Queue()
        self.logger = TraceFileLogger(self.queue, 'test', self.target_dir)
        self.logger.flush_interval = 2
        self.flush_interval = 2
        self.thread = threading.Thread(target=self.logger.run)
        self.thread.start()

    def tearDown(self) -> None:
        if not self.logger.closed:
            self.logger.close()
        self.thread.join(2)
        shutil.rmtree(self.target_dir)

    @timeout_decorator.timeout(5)
    def assert_flush(self, n):
        with open(self.logger.file_path, 'r') as fd:
            # do not count header
            self.assertEqual(len(fd.readlines()) - 1, n)

    @timeout_decorator.timeout(5)
    def count_traces(self) -> int:
        with open(self.logger.file_path, 'r') as fd:
            # do not count header
            return len(fd.readlines()) - 1

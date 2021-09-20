import multiprocessing
import queue
import threading
import unittest
from unittest.mock import patch

import pymq
import redis
from galileodb.trace import START, PAUSE
from pymq.provider.redis import RedisConfig
from timeout_decorator import timeout_decorator

from galileo.worker.api import RegisterWorkerEvent, StartTracingCommand, PauseTracingCommand
from galileo.worker.context import Context
from galileo.worker.daemon import WorkerDaemon
from tests.testutils import RedisResource


class MockQueue:

    def __init__(self):
        super().__init__()
        self.traces = queue.Queue()
        self.delegate = multiprocessing.Queue()

    def put(self, *args, **kwargs) -> None:
        self.traces.put(args[0])
        self.delegate.put(*args, **kwargs)

    def __getattr__(self, item):
        if hasattr(self.delegate, item):
            return getattr(self.delegate, item)
        raise AttributeError


class WorkerTest(unittest.TestCase):
    redis_resource = RedisResource()
    eventbus: pymq.EventBus

    def setUp(self) -> None:
        self.redis_resource.setUp()
        self.eventbus = pymq.init(RedisConfig(self.redis_resource.rds))

    def tearDown(self) -> None:
        pymq.shutdown()
        self.redis_resource.tearDown()

    @timeout_decorator.timeout(5)
    def test_worker_start_register(self):
        rds = self.redis_resource.rds

        class TestContext(Context):
            def create_redis(self) -> redis.Redis:
                return rds

        register_event = threading.Event()

        def register_listener(event: RegisterWorkerEvent):
            register_event.set()

        self.eventbus.subscribe(register_listener)

        ctx = TestContext()

        worker = WorkerDaemon(ctx, eventbus=self.eventbus)

        worker_thread = threading.Thread(target=worker.run)
        worker_thread.start()

        self.assertTrue(register_event.wait(2), 'did not receive register event')

        worker.close()

        worker_thread.join()

    @timeout_decorator.timeout(5)
    def test_worker_start_logger(self):
        self.assert_msg_in_queue_after_cmd(StartTracingCommand(), START)

    @timeout_decorator.timeout(5)
    def test_worker_pause_logger(self):
        self.assert_msg_in_queue_after_cmd(PauseTracingCommand(), PAUSE)

    def assert_msg_in_queue_after_cmd(self, cmd, msg):
        trace_queue = MockQueue()

        started = threading.Event()

        def started_listener(event: RegisterWorkerEvent):
            started.set()

        self.eventbus.subscribe(started_listener)

        with patch.object(WorkerDaemon, '_create_trace_queue', return_value=trace_queue):
            rds = self.redis_resource.rds

            class TestContext(Context):
                def create_redis(self) -> redis.Redis:
                    return rds

            ctx = TestContext()

            worker = WorkerDaemon(ctx, eventbus=self.eventbus)

            worker_thread = threading.Thread(target=worker.run)
            worker_thread.start()

            started.wait(3)

            self.eventbus.publish(cmd)

            got = trace_queue.traces.get()
            self.assertEqual(msg, got)
            worker.close()
            worker_thread.join()

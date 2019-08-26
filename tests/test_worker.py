import threading
import unittest

import pymq
import redis
from pymq.provider.redis import RedisConfig
from timeout_decorator import timeout_decorator

from galileo.event import RegisterEvent
from galileo.worker import ExperimentWorker, Context
from tests.testutils import RedisResource


class WorkerTest(unittest.TestCase):
    redis_resource = RedisResource()

    @classmethod
    def setUpClass(cls) -> None:
        cls.redis_resource.setUp()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.redis_resource.tearDown()

    def setUp(self) -> None:
        pymq.init(RedisConfig(self.redis_resource.rds))

    def tearDown(self) -> None:
        pymq.shutdown()

    @timeout_decorator.timeout(5)
    def test_worker_start_register(self):
        rds = self.redis_resource.rds

        class TestContext(Context):
            def create_redis(self) -> redis.Redis:
                return rds

        register_event = threading.Event()

        def register_listener(event: RegisterEvent):
            register_event.set()

        pymq.subscribe(register_listener)

        ctx = TestContext()

        worker = ExperimentWorker(ctx, [])

        worker_thread = threading.Thread(target=worker.run)
        worker_thread.start()

        self.assertTrue(register_event.wait(2), 'did not receive register event')

        worker.close()

        worker_thread.join()

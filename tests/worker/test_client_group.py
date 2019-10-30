import multiprocessing
import os
import signal
import threading
import unittest
from time import sleep
from typing import List, Callable
from unittest.mock import patch

import pymq
import redis
from pymq.exceptions import RemoteInvocationError
from pymq.provider.redis import RedisConfig

from galileo.apps import AppInfo
from galileo.apps.app import AppClient, AppRequest
from galileo.apps.loader import AppClientLoader
from galileo.experiment.model import ServiceRequestTrace
from galileo.util import poll
from galileo.worker import client_group
from galileo.worker.api import ClientConfig, SetRpsCommand, StartClientsCommand, CloseClientGroupCommand
from galileo.worker.client_group import ClientGroup
from galileo.worker.context import Context
from tests.testutils import RedisResource


def setup_context(rds) -> Context:
    app_info = AppInfo('mock_app', dict())

    class MockAppClient(AppClient):

        def next_request(self) -> AppRequest:
            return AppRequest('mock_app', 'mock_method', 'mock_endpoint', dict())

    class MockAppLoader(AppClientLoader):

        def list(self) -> List[AppInfo]:
            return [app_info]

        def load(self, name, parameters=None) -> AppClient:
            return MockAppClient(None, None, None)

    app_loader = MockAppLoader()

    class MockContext(Context):

        @property
        def worker_name(self):
            return 'mock-worker'

        def create_redis(self) -> redis.Redis:
            return rds

        def create_app_loader(self) -> AppClientLoader:
            return app_loader

    env = dict(os.environ)
    env['galileo_router_type'] = 'DebugRouter'
    return MockContext(env)


class TestClientGroup(unittest.TestCase):
    rds_resource: RedisResource = RedisResource()
    client_group: ClientGroup
    context: Context
    trace_queue: multiprocessing.Queue
    gid: str
    client_cfg: ClientConfig

    def setUp(self) -> None:
        self.rds = self.init_rds()
        pymq.init(RedisConfig(self.rds))
        self.context = setup_context(self.rds)
        self.client_cfg = ClientConfig('mock_app', 'mock_app')
        self.trace_queue = multiprocessing.Queue()
        self.gid = 'mock:gid'

    def tearDown(self) -> None:
        if self.client_group:
            self.client_group.close()
        pymq.shutdown()
        self.rds_resource.tearDown()

    def test_client_group_info(self):
        self.start_group()

        def check_client_group(response) -> bool:
            return response and response['gid'] == self.gid and response['worker'] == self.context.worker_name \
                   and response['rps'] == [0, 'none'] and response['queued_requests'] == 0 \
                   and response['clients'] == 0

        self.assert_info_response(lambda resp: check_client_group(resp))

    def test_client_group_start_client(self):
        self.start_group()

        pymq.publish(StartClientsCommand(self.gid, 1))
        self.assert_info_response(lambda response: response['clients'] == 1)

    def test_client_group_sends_requests(self):
        self.start_group()

        rps = 10
        dist = 'constant'
        pymq.publish(StartClientsCommand(self.gid))

        self.assert_info_response(lambda resp: resp['clients'] > 0)

        pymq.publish(SetRpsCommand(self.gid, rps, dist=dist))

        self.assert_info_response(lambda resp: resp['rps'] == [rps, dist])

        req: ServiceRequestTrace = self.trace_queue.get(timeout=1)

        self.assertEqual(self.client_cfg.service, req.service)

    def test_client_group_rps_command(self):
        self.start_group()

        rps = 10
        dist = 'constant'
        pymq.publish(SetRpsCommand(self.gid, rps, dist=dist))

        self.assert_info_response(lambda resp: resp['rps'] == [rps, dist])

    def test_client_close(self):
        self.client_group = ClientGroup(self.gid, self.client_cfg, self.trace_queue, ctx=self.context)
        threading.Thread(target=self.client_group.run).start()
        self.client_group.close()

        self.assertTrue(self.client_group._closed)

    def assert_client_group_lives(self):
        self.assert_info_response(lambda response: response and response['gid'] == self.gid)

    @staticmethod
    def assert_info_response(check: Callable[[dict], bool]):
        info = pymq.stub(ClientGroup.info, 1)

        def check_client_group_lives() -> bool:
            response = info()
            return response and check(response)

        poll(lambda: check_client_group_lives(), 2, 0.1)

    def start_group(self):
        self.client_group = ClientGroup(self.gid, self.client_cfg, self.trace_queue, ctx=self.context)
        client_group_process = threading.Thread(target=self.client_group.run)
        client_group_process.start()
        self.assert_client_group_lives()

    def init_rds(self):
        self.rds_resource.setUp()
        return self.rds_resource.rds


class TestRunClientGroup(unittest.TestCase):
    redis_resource: RedisResource = RedisResource()
    context: Context
    gid: str
    client_cfg: ClientConfig
    trace_queue: multiprocessing.Queue

    def setUp(self) -> None:
        self.redis_resource.setUp()
        self.rds = self.redis_resource.rds
        pymq.init(RedisConfig(self.rds))
        self.gid = 'run:gid'
        self.client_cfg = ClientConfig('mock_run', 'mock_run')
        self.trace_queue = multiprocessing.Queue()
        self.context = setup_context(self.rds)

    def tearDown(self) -> None:
        os.kill(self.process.pid, signal.SIGINT)
        sleep(2)
        pymq.shutdown()
        self.redis_resource.tearDown()

    def test_run_starts_client_group(self):
        self.process = multiprocessing.Process(target=client_group.run,
                                               args=(self.gid, self.client_cfg, self.trace_queue, self.context))
        self.process.start()
        self.assert_client_group_lives()

    def test_run_closes_client_group_on_signal(self):
        self.process = multiprocessing.Process(target=client_group.run,
                                               args=(self.gid, self.client_cfg, self.trace_queue, self.context))
        self.process.start()
        self.assert_client_group_lives()

        os.kill(self.process.pid, signal.SIGINT)

        def check_process_not_lives() -> bool:
            try:
                info = pymq.stub(ClientGroup.info, timeout=1)
                if info() is None:
                    return True
            except RemoteInvocationError:
                # expected, because client group should be closed
                return True
            return False

        poll(lambda: check_process_not_lives(), 2, 0.1)

    @patch('galileo.worker.client_group.ClientGroup.__init__')
    def test_run_sends_close_command_after_faulty_group_construction(self, init):
        def side_effect(*args, **kwargs):
            raise ValueError()

        init.side_effect = side_effect
        event = threading.Event()

        def on_close(cmd: CloseClientGroupCommand):
            self.assertEqual(cmd.gid, self.gid)
            event.set()

        pymq.subscribe(on_close)
        self.process = multiprocessing.Process(target=client_group.run,
                                               args=(self.gid, self.client_cfg, self.trace_queue, self.context))
        self.process.start()

        poll(lambda: event.is_set(), 2, 0.1)

    def assert_client_group_lives(self):
        self.assert_info_response(lambda response: response and response['gid'] == self.gid)

    @staticmethod
    def assert_info_response(check: Callable[[dict], bool]):
        info = pymq.stub(ClientGroup.info, 1)

        def check_client_group_lives() -> bool:
            response = info()
            return response and check(response)

        poll(lambda: check_client_group_lives(), 2, 0.1)

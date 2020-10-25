import os
import time
import unittest
from queue import Queue
from typing import NamedTuple
from unittest.mock import patch

from pymq.provider.simple import SimpleEventBus

from galileo.routing import ServiceRequest, RedisRoutingTable, RoutingRecord
from galileo.worker.api import ClientDescription, ClientConfig
from galileo.worker.client import Client
from galileo.worker.context import Context
from tests.testutils import RedisResource
from tests.worker.test_client import StaticRequestGenerator


class TestSingleRequest(unittest.TestCase):
    n = 10000

    redis_resource = RedisResource()

    def setUp(self) -> None:
        self.redis_resource.setUp()
        self.rds = self.redis_resource.rds
        self.rtbl = RedisRoutingTable(self.rds)

    def tearDown(self) -> None:
        self.redis_resource.tearDown()

    def test_debug_router(self):
        env = dict(os.environ)
        env['galileo_router_type'] = 'DebugRouter'

        client_id = 'unittest_client'
        ctx = Context(env)
        trace_queue = Queue()

        description = ClientDescription(client_id, 'unittest_worker', ClientConfig('aservice'))
        # ctx: Context, trace_queue: Queue, description: ClientDescription

        client = Client(ctx, trace_queue, description, eventbus=SimpleEventBus())
        client.request_generator = StaticRequestGenerator([ServiceRequest('aservice') for _ in range(self.n)])

        then = time.time()
        client.run()
        now = time.time()

        total = now - then

        print('DebugRouter: %.2f req/sec (%.4fs total)' % (self.n / total, total))

    @patch('galileo.routing.router.requests.request')
    def test_symmetry_router(self, mock_request):
        # mock http server
        Response = NamedTuple('Response', status_code=int, text=str, url=str, method=str)

        def fake_response(method, url):
            return Response(200, 'ok', url, method)

        mock_request.side_effect = fake_response

        self.rtbl.set_routing(RoutingRecord('aservice', ['host1', 'host2', 'host3'], [1, 2, 3]))

        env = dict(os.environ)
        env['galileo_router_type'] = 'CachingSymmetryHostRouter'

        client_id = 'unittest_client'
        ctx = Context(env)
        ctx.create_redis = lambda: self.rds
        trace_queue = Queue()

        description = ClientDescription(client_id, 'unittest_worker', ClientConfig('aservice'))
        # ctx: Context, trace_queue: Queue, description: ClientDescription

        client = Client(ctx, trace_queue, description, eventbus=SimpleEventBus())
        client.request_generator = StaticRequestGenerator([ServiceRequest('aservice') for _ in range(self.n)])

        then = time.time()
        client.run()
        now = time.time()

        total = now - then

        print('CachingSymmetryHostRouter: %.2f req/sec (%.4f total)' % (self.n / total, total))

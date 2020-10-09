import os
import time
import unittest
from queue import Queue
from typing import List

from symmetry.gateway import ServiceRequest
from timeout_decorator import timeout_decorator

from galileo.worker.api import ClientDescription, ClientConfig
from galileo.worker.client import Client
from galileo.worker.context import Context, DebugRouter


class StaticRequestGenerator:

    def __init__(self, requests: List[ServiceRequest]) -> None:
        super().__init__()
        self.requests = requests

    def run(self):
        yield from self.requests

    def close(self):
        pass

    def set_rps(self, *args, **kwargs):
        pass


class ClientTest(unittest.TestCase):

    @timeout_decorator.timeout(5)
    def test_client_integration(self):
        env = dict(os.environ)
        env['galileo_router_type'] = 'DebugRouter'

        client_id = 'unittest_client'
        ctx = Context(env)
        trace_queue = Queue()

        description = ClientDescription(client_id, 'unittest_worker', ClientConfig('aservice'))
        # ctx: Context, trace_queue: Queue, description: ClientDescription

        client = Client(ctx, trace_queue, description)

        client.request_generator = StaticRequestGenerator([
            ServiceRequest('aservice'),
            ServiceRequest('aservice'),
        ])

        client.run()

        trace1 = trace_queue.get(timeout=2)
        trace2 = trace_queue.get(timeout=2)

        self.assertEqual('aservice', trace1.service)
        self.assertEqual('aservice', trace2.service)

        self.assertEqual('debughost', trace1.host)
        self.assertEqual('debughost', trace2.host)

        now = time.time()
        self.assertAlmostEqual(now, trace1.done, delta=2)
        self.assertAlmostEqual(now, trace2.done, delta=2)

    @timeout_decorator.timeout(5)
    def test_with_router_fault(self):
        class FaultInjectingRouter(DebugRouter):
            def request(self, req: ServiceRequest) -> 'requests.Response':
                if req.path == '/api/nonexisting':
                    raise ValueError('some error')

                return super().request(req)

        router = FaultInjectingRouter()

        ctx = Context()
        ctx.create_router = lambda: router
        client_id = 'unittest_client'
        trace_queue = Queue()

        description = ClientDescription(client_id, 'unittest_worker', ClientConfig('aservice'))
        # ctx: Context, trace_queue: Queue, description: ClientDescription

        client = Client(ctx, trace_queue, description)

        client.request_generator = StaticRequestGenerator([
            ServiceRequest('aservice', path='/api/nonexisting'),
            ServiceRequest('aservice', path='/api/unittest'),
        ])

        client.run()

        trace1 = trace_queue.get(timeout=2)
        trace2 = trace_queue.get(timeout=2)

        self.assertEqual(-1, trace1.sent)
        self.assertAlmostEqual(trace2.sent, time.time(), delta=2)

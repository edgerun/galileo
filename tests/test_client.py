import os
import time
import unittest
from queue import Queue

import requests
from symmetry.gateway import ServiceRequest
from timeout_decorator import timeout_decorator

import galileo.worker.client as client
from galileo.worker.context import Context, DebugRouter


class ClientTest(unittest.TestCase):

    @timeout_decorator.timeout(5)
    def test_client_integration(self):
        env = dict(os.environ)
        env['galileo_router_type'] = 'DebugRouter'

        client_id = 'unittest_client'
        ctx = Context(env)
        request_queue = Queue()
        trace_queue = Queue()

        request_queue.put(ServiceRequest('aservice', path='/api/unittest'))
        request_queue.put(ServiceRequest('aservice', path='/api/unittest'))
        request_queue.put(client.POISON)

        client.run(client_id, ctx, request_queue, trace_queue)

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
            def request(self, req: ServiceRequest) -> requests.Response:
                if req.path == '/api/nonexisting':
                    raise ValueError('some error')

                return super().request(req)

        router = FaultInjectingRouter()

        ctx = Context()
        ctx.create_router = lambda: router
        client_id = 'unittest_client'
        request_queue = Queue()
        trace_queue = Queue()

        request_queue.put(ServiceRequest('aservice', path='/api/nonexisting'))
        request_queue.put(ServiceRequest('aservice', path='/api/unittest'))
        request_queue.put(client.POISON)

        client.run(client_id, ctx, request_queue, trace_queue)

        trace1 = trace_queue.get(timeout=2)
        trace2 = trace_queue.get(timeout=2)

        self.assertEqual(-1, trace1.sent)
        self.assertAlmostEqual(trace2.sent, time.time(), delta=2)

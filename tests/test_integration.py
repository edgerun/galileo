import os
import threading
import unittest
from http.server import HTTPServer, BaseHTTPRequestHandler
from queue import Queue
from typing import List

import pymq
from galileodb.model import RequestTrace
from galileodb.recorder.traces import RedisTraceRecorder
from galileodb.trace import TraceWriter
from pymq.provider.redis import RedisConfig
from timeout_decorator import timeout_decorator

from galileo.controller import RedisClusterController
from galileo.routing import RedisRoutingTable, RoutingRecord
from galileo.shell.shell import Galileo
from galileo.util import poll
from galileo.worker.daemon import WorkerDaemon
from tests.testutils import assert_poll, RedisResource


class TestIntegration(unittest.TestCase):
    redis_resource = RedisResource()

    def setUp(self) -> None:
        # Create redis server
        self.redis_resource.setUp()
        self.rds = self.redis_resource.rds
        self.rds.flushall()

        self.eventbus = pymq.init(RedisConfig(self.rds))
        self.ctrl = RedisClusterController(self.rds)
        self.rtbl = RedisRoutingTable(self.rds)

    def tearDown(self) -> None:
        pymq.shutdown()
        self.redis_resource.tearDown()

    @timeout_decorator.timeout(30)
    def test_single_client_scenario(self):
        os.environ['galileo_redis_host'] = 'file://' + self.redis_resource.tmpfile
        os.environ['galileo_trace_logging'] = 'redis'
        os.environ['galileo_router_type'] = 'SymmetryHostRouter'

        # setup up http app
        class HttpHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'ok')
                return

        httpd = HTTPServer(('localhost', 31523), HttpHandler)
        t_http = threading.Thread(target=httpd.serve_forever, daemon=True)
        t_http.start()

        # start a worker instance
        worker = WorkerDaemon()
        t_worker = threading.Thread(target=worker.run, daemon=True)
        t_worker.start()

        # start traces subscriber
        traces = Queue()

        class QueueTraceWriter(TraceWriter):
            def write(self, data: List[RequestTrace]):
                for d in data:
                    traces.put(d)

        recorder = RedisTraceRecorder(self.rds, exp_id='exp_01', writer=QueueTraceWriter(), flush_every=1)
        recorder.start()

        try:
            # set rtbl record
            self.rtbl.set_routing(RoutingRecord('myservice', ['localhost:31523'], [1]))

            g = Galileo(self.ctrl)

            # test a single request and make sure everything works so far
            response = g.request('myservice')
            self.assertEqual('ok', response.text)

            # wait for worker to be up
            self.assertEqual(1, len(g.ping()))

            # start tracing
            g.start_tracing()

            # spawn a client group
            c = g.spawn('myservice')

            # wait for the client to appear
            assert_poll(lambda: pymq.stub('Client.get_info')() is not None, msg='client did not appear')

            # make sure client was registered
            assert_poll(lambda: len(self.ctrl.list_clients()) >= 1, msg='client was not registered')

            # send three requests and wait for them to finish
            c.request(n=3).wait(2)

            # close clients
            c.close()

            # wait for them to disappear
            assert_poll(lambda: len(self.ctrl.list_clients()) == 0, msg='client was not closed')

            # should flush traces to redis
            g.stop_tracing()

            # check the first trace fully
            t: RequestTrace = traces.get(timeout=5)
            self.assertEqual(200, t.status)
            self.assertEqual('ok', t.response)
            self.assertEqual('myservice', t.service)
            self.assertEqual('localhost:31523', t.server)

            # check that the others are successful
            t: RequestTrace = traces.get(timeout=2)
            self.assertEqual(200, t.status)
            t: RequestTrace = traces.get(timeout=2)
            self.assertEqual(200, t.status)

            self.assertEqual(0, traces.qsize(), 'expected trace queue to have exactly three entries')

        finally:
            worker.close()
            httpd.shutdown()
            httpd.server_close()
            recorder.stop(2)

        recorder.join(2)
        t_worker.join(2)
        t_http.join(2)

        # wait for client to be gone to safely shutdown redis
        poll(lambda: pymq.stub('Client.get_info', timeout=0.5)() is None, timeout=2)

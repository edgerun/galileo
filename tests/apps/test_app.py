import unittest

from galileo.apps.app import DefaultAppClient
from galileo.worker.client import AppClientRequestFactory


class DefaultAppClientTest(unittest.TestCase):

    def test_with_factory(self):
        client = DefaultAppClient()
        factory = AppClientRequestFactory('myservice', client)

        req = factory.create_request()

        self.assertEqual('myservice', req.service)
        self.assertEqual('/', req.path)
        self.assertEqual('get', req.method)
        self.assertEqual({}, req.kwargs)

    def test_with_parameters_and_factory(self):
        client = DefaultAppClient({'method': 'post', 'path': '/foo', 'kwargs': {'data': '500'}})
        factory = AppClientRequestFactory('myservice', client)

        req = factory.create_request()

        self.assertEqual('myservice', req.service)
        self.assertEqual('/foo', req.path)
        self.assertEqual('post', req.method)
        self.assertEqual({'data': '500'}, req.kwargs)

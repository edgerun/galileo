from time import sleep

import pymq

from galileo.event import RegisterEvent
from tests.api import ResourceTest


class TestHostResource(ResourceTest):

    def test_get_empty_hosts(self):
        result = self.simulate_get('/api/hosts')

        self.assertEqual(result.json, [])

    def test_get_hosts(self):
        hosts = ['host1', 'host2']
        pymq.publish(RegisterEvent('host1'))
        pymq.publish(RegisterEvent('host2'))

        # sleep to publish events and add hosts to redis
        sleep(0.5)

        result = self.simulate_get('/api/hosts')
        self.assertIsNotNone(result.json, 'response must not be empty')
        self.assertCountEqual(result.json, hosts)
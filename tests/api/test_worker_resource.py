from time import sleep

from tests.api import ResourceTest


class TestHostResource(ResourceTest):

    def test_get_empty_hosts(self):
        result = self.simulate_get('/api/worker')

        self.assertEqual(result.json, [])

    def test_get_worker(self):
        hosts = ['host1', 'host2']

        self.ctx.cctrl.register_worker('host1')
        self.ctx.cctrl.register_worker('host2')

        # sleep to publish events and add hosts to redis
        sleep(0.5)

        result = self.simulate_get('/api/worker')
        self.assertIsNotNone(result.json, 'response must not be empty')
        self.assertCountEqual(result.json, hosts)

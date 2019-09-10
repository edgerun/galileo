import unittest

from tests.api import ResourceTest


class TestServiceResource(ResourceTest):
    def test_get_services(self):
        services = [
            {
                'name': 'mxnet-model-server'
            }
        ]

        result = self.simulate_get('/api/services')

        self.assertEqual(result.json, services)


if __name__ == '__main__':
    unittest.main()

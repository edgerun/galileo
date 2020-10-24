import time
import unittest

from timeout_decorator import timeout_decorator

from galileo.routing.table import RoutingTable, RoutingRecord, RedisRoutingTable, ReadOnlyListeningRedisRoutingTable
from tests.testutils import RedisResource


class TestRoutingTable(unittest.TestCase):
    redis = RedisResource()
    rtbl: RoutingTable

    def setUp(self) -> None:
        self.redis.setUp()
        self.rtbl = RedisRoutingTable(self.redis.rds)

    def tearDown(self) -> None:
        self.rtbl.clear()
        self.redis.tearDown()

    def test_get_routes_on_empty_table_returns_empty_list(self):
        routes = self.rtbl.get_routes()
        self.assertEqual(0, len(routes))

    def test_set_routing(self):
        record = RoutingRecord('aservice', ['ahost', 'bhost'], [1.0, 2.0])
        self.rtbl.set_routing(record)

        routes = self.rtbl.get_routes()
        self.assertEqual(1, len(routes))
        self.assertEqual(record, routes[0])

    def test_list_services(self):
        self.rtbl.set_routing(RoutingRecord('aservice', ['ahost', 'bhost'], [1.0, 2.0]))
        self.rtbl.set_routing(RoutingRecord('bservice', ['ahost', 'bhost'], [1.0, 2.0]))

        services = self.rtbl.list_services()
        self.assertIn('aservice', services)
        self.assertIn('bservice', services)
        self.assertEqual(2, len(services))

    def test_remove_service(self):
        self.rtbl.set_routing(RoutingRecord('aservice', ['ahost', 'bhost'], [1.0, 2.0]))
        self.rtbl.set_routing(RoutingRecord('bservice', ['ahost', 'bhost'], [2.0, 3.0]))

        self.rtbl.remove_service('aservice')

        routes = self.rtbl.get_routes()
        self.assertEqual(1, len(routes))
        self.assertEqual('bservice', routes[0].service)

        services = self.rtbl.list_services()
        self.assertNotIn('aservice', services)

    def test_get_routing_of_non_existing_service(self):
        self.rtbl.set_routing(RoutingRecord('aservice', ['ahost', 'bhost'], [1.0, 2.0]))
        self.assertRaises(ValueError, self.rtbl.get_routing, 'bservice')

    def test_set_routing_invalid_record(self):
        record = RoutingRecord('aservice', ['ahost', 'bhost'], [1.0])
        self.assertRaises(ValueError, self.rtbl.set_routing, record)
        self.assertEqual(0, len(self.rtbl.get_routes()))

        record = RoutingRecord('aservice', ['ahost'], [1.0, 2.0])
        self.assertRaises(ValueError, self.rtbl.set_routing, record)
        self.assertEqual(0, len(self.rtbl.get_routes()))

    @timeout_decorator.timeout(5)
    def test_notification_on_set(self):
        pubsub = self.redis.rds.pubsub()

        pubsub.subscribe(RedisRoutingTable.update_channel)

        listener = pubsub.listen()

        next(listener)  # subscription message

        self.rtbl.set_routing(RoutingRecord('aservice', ['ahost', 'bhost'], [2.0, 3.0]))
        msg = next(listener)  # subscription message
        self.assertEqual('aservice', msg['data'])

        self.rtbl.set_routing(RoutingRecord('bservice', ['ahost', 'bhost'], [2.0, 3.0]))
        msg = next(listener)  # subscription message
        self.assertEqual('bservice', msg['data'])

        self.rtbl.remove_service('bservice')
        msg = next(listener)  # subscription message
        self.assertEqual('bservice', msg['data'])

        pubsub.unsubscribe(RedisRoutingTable.update_channel)
        pubsub.close()


class TestListeningTable(unittest.TestCase):
    redis = RedisResource()
    rtbl_mutable: RoutingTable

    def setUp(self) -> None:
        self.redis.setUp()
        self.rtbl_mutable = RedisRoutingTable(self.redis.rds)
        self.rtbl = ReadOnlyListeningRedisRoutingTable(self.redis.rds)
        self.rtbl.start()

    def tearDown(self) -> None:
        self.rtbl_mutable.clear()
        self.rtbl.stop(2)
        self.redis.tearDown()

    def test_cache_returns_same_object(self):
        self.rtbl_mutable.set_routing(RoutingRecord('aservice', ['ahost', 'bhost'], [2.0, 3.0]))

        record1 = self.rtbl.get_routing('aservice')
        record2 = self.rtbl.get_routing('aservice')

        self.assertEqual(id(record1), id(record2))

    def test_get_routing_after_update_returns_correct_value(self):
        # FIXME use polling

        self.rtbl_mutable.set_routing(RoutingRecord('aservice', ['ahost', 'bhost'], [2.0, 3.0]))
        record1 = self.rtbl.get_routing('aservice')

        self.rtbl_mutable.set_routing(RoutingRecord('aservice', ['ahost'], [2.0]))
        time.sleep(0.25)
        record2 = self.rtbl.get_routing('aservice')

        self.assertNotEqual(id(record1), id(record2))
        self.assertEqual('ahost', record2.hosts[0])
        self.assertEqual(1, len(record2.hosts))

    def test_list_services_returns_correct_services(self):
        # FIXME use polling

        self.rtbl_mutable.set_routing(RoutingRecord('aservice', ['ahost', 'bhost'], [2.0, 3.0]))
        time.sleep(0.25)
        self.assertIn('aservice', self.rtbl.list_services())
        self.assertEqual(1, len(self.rtbl.list_services()))

        self.rtbl_mutable.set_routing(RoutingRecord('bservice', ['ahost', 'bhost'], [2.0, 3.0]))
        time.sleep(0.25)
        self.assertIn('aservice', self.rtbl.list_services())
        self.assertIn('bservice', self.rtbl.list_services())
        self.assertEqual(2, len(self.rtbl.list_services()))

        self.rtbl_mutable.remove_service('aservice')
        time.sleep(0.25)
        self.assertIn('bservice', self.rtbl.list_services())
        self.assertEqual(1, len(self.rtbl.list_services()))


if __name__ == '__main__':
    unittest.main()

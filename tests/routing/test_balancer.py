import unittest
import unittest.mock
from collections import Counter, defaultdict

from galileo.routing.balancer import WeightedRandomBalancer, WeightedRoundRobinBalancer
from galileo.routing.table import RoutingTable, RoutingRecord


class BalancerTest(unittest.TestCase):

    def test_weighted_random(self):
        services = ['aservice']
        route = RoutingRecord('aservice', hosts=['a', 'b'], weights=[2, 4])  # 0.333 / 0.666

        rtbl = RoutingTable()
        rtbl.list_services = unittest.mock.MagicMock(return_value=services)
        rtbl.get_routing = unittest.mock.MagicMock(return_value=route)

        balancer = WeightedRandomBalancer(rtbl)

        hosts = []
        for i in range(100):
            hosts.append(balancer.next_host('aservice'))

        cnt = Counter(hosts)

        self.assertAlmostEqual(33, cnt['a'], delta=15)
        self.assertAlmostEqual(66, cnt['b'], delta=15)

    def test_weighted_round_robin(self):
        services = ['aservice']
        route = RoutingRecord('aservice', hosts=['a', 'b', 'c'], weights=[1, 4, 5])  # 0.1 / 0.4 / 0.5

        rtbl = RoutingTable()
        rtbl.list_services = unittest.mock.MagicMock(return_value=services)
        rtbl.get_routing = unittest.mock.MagicMock(return_value=route)

        balancer = WeightedRoundRobinBalancer(rtbl)

        hosts = []
        for i in range(100):
            hosts.append(balancer.next_host('aservice'))

        cnt = Counter(hosts)

        self.assertAlmostEqual(10, cnt['a'], delta=1)
        self.assertAlmostEqual(40, cnt['b'], delta=1)
        self.assertAlmostEqual(50, cnt['c'], delta=1)

    def test_weighted_round_robin_multiple_services(self):
        services = ['aservice', 'bservice']

        def get_routing(service):
            if service == 'aservice':
                return RoutingRecord('aservice', hosts=['a', 'b', 'c'], weights=[1, 4, 5])
            elif service == 'bservice':
                return RoutingRecord('bservice', hosts=['a', 'd'], weights=[2, 8])
            else:
                raise ValueError

        rtbl = RoutingTable()
        rtbl.list_services = unittest.mock.MagicMock(return_value=services)
        rtbl.get_routing = unittest.mock.MagicMock(side_effect=get_routing)

        balancer = WeightedRoundRobinBalancer(rtbl)

        hosts = defaultdict(list)
        for _ in range(50):
            hosts['aservice'].append(balancer.next_host('aservice'))
        for _ in range(50):
            hosts['bservice'].append(balancer.next_host('bservice'))
        for _ in range(50):
            hosts['aservice'].append(balancer.next_host('aservice'))
            hosts['bservice'].append(balancer.next_host('bservice'))

        cnt_a = Counter(hosts['aservice'])
        self.assertAlmostEqual(10, cnt_a['a'], delta=1)
        self.assertAlmostEqual(40, cnt_a['b'], delta=1)
        self.assertAlmostEqual(50, cnt_a['c'], delta=1)

        cnt_b = Counter(hosts['bservice'])
        self.assertAlmostEqual(20, cnt_b['a'], delta=1)
        self.assertAlmostEqual(80, cnt_b['d'], delta=1)

    def test_weighted_round_robin_removing_hosts(self):
        rtbl = RoutingTable()
        rtbl.list_services = unittest.mock.MagicMock(return_value=['aservice'])
        rtbl.get_routing = unittest.mock.MagicMock(
            return_value=RoutingRecord('aservice', hosts=['a', 'b', 'c', 'd'], weights=[1, 1, 1, 1]))

        balancer = WeightedRoundRobinBalancer(rtbl)

        for _ in range(50):
            balancer.next_host('aservice')

        rtbl.get_routing = unittest.mock.MagicMock(
            return_value=RoutingRecord('aservice', hosts=['a', 'b', 'c'], weights=[1, 4, 5]))

        hosts = []
        for i in range(100):
            hosts.append(balancer.next_host('aservice'))

        cnt = Counter(hosts)

        self.assertAlmostEqual(10, cnt['a'], delta=1)
        self.assertAlmostEqual(40, cnt['b'], delta=1)
        self.assertAlmostEqual(50, cnt['c'], delta=1)

    def test_weighted_round_robin_adding_hosts(self):
        rtbl = RoutingTable()
        rtbl.list_services = unittest.mock.MagicMock(return_value=['aservice'])
        rtbl.get_routing = unittest.mock.MagicMock(
            return_value=RoutingRecord('aservice', hosts=['a', 'b'], weights=[1, 1]))

        balancer = WeightedRoundRobinBalancer(rtbl)

        for _ in range(50):
            balancer.next_host('aservice')

        rtbl.get_routing = unittest.mock.MagicMock(
            return_value=RoutingRecord('aservice', hosts=['a', 'b', 'c'], weights=[1, 4, 5]))

        hosts = []
        for i in range(100):
            hosts.append(balancer.next_host('aservice'))

        cnt = Counter(hosts)

        self.assertAlmostEqual(10, cnt['a'], delta=1)
        self.assertAlmostEqual(40, cnt['b'], delta=1)
        self.assertAlmostEqual(50, cnt['c'], delta=1)

import abc
import math
import random
import threading
from functools import reduce

from galileo.routing.table import RoutingTable


class Balancer(abc.ABC):

    def next_host(self, service=None):
        raise NotImplementedError


class StaticHostBalancer(Balancer):
    host: str

    def __init__(self, host) -> None:
        super().__init__()
        self.host = host

    def next_host(self, service=None):
        return self.host


class StaticLocalhostBalancer(StaticHostBalancer):

    def __init__(self) -> None:
        super().__init__('localhost')


class WeightedRandomBalancer(Balancer):
    _rtbl: RoutingTable

    def __init__(self, rtbl: RoutingTable) -> None:
        super().__init__()
        self._rtbl = rtbl

    def next_host(self, service=None):
        if not service:
            raise ValueError

        record = self._rtbl.get_routing(service)
        host = random.choices(record.hosts, record.weights, k=1)[0]

        return host


def gcd(ls):
    return reduce(math.gcd, ls)


class WeightedRoundRobinBalancer(Balancer):
    """
    Implementation of http://kb.linuxvirtualserver.org/wiki/Weighted_Round-Robin_Scheduling

    FIXME: generators are never freed
    """

    def __init__(self, rtbl: RoutingTable) -> None:
        super().__init__()
        self._rtbl = rtbl
        self._generators = dict()  # service name -> generator
        self._lock = threading.Lock()

    def generator(self, service):
        i = -1
        cw = 0

        while True:
            record = self._rtbl.get_routing(service)

            hosts = record.hosts
            weights = [int(w) for w in record.weights]

            n = len(hosts)
            i = (i + 1) % n
            if i == 0:
                cw = cw - gcd(weights)
                if cw <= 0:
                    cw = max(weights)
                    if cw == 0:
                        raise ValueError

            if weights[i] >= cw:
                yield hosts[i]

    def _require_generator(self, service):
        gen = self._generators.get(service)
        if gen:
            return gen

        with self._lock:
            if service in self._generators:  # avoid race condition
                return self._generators[service]

            gen = self.generator(service)
            self._generators[service] = gen
            return gen

    def next_host(self, service=None):
        if not service:
            raise ValueError

        gen = self._require_generator(service)
        return next(gen)

import os
import sys
import time
from typing import List, Dict

import pymq
from pymq.provider.redis import RedisConfig
from symmetry.api import RoutingRecord, RoutingTable
from symmetry.routing import RedisRoutingTable

from galileo.controller.cluster import ClusterController, RedisClusterController
from galileo.shell.printer import sprint_routing_table, print_tabular, Stringer
from galileo.worker.api import ClientConfig, ClientDescription, CloseClientCommand

prompt = 'galileo> '

banner = r"""
                                   __  __
 .-.,="``"=.          ____ _____ _/ (_) /__  ____
 '=/_       \        / __ `/ __ `/ / / / _ \/ __ \
  |  '=._    |      / /_/ / /_/ / / / /  __/ /_/ /
   \     `=./`.     \__, /\__,_/_/_/_/\___/\____/
    '=.__.=' `='   /____/

"""

usage = Stringer('''the galileo shell is an interactive python shell that provides the following commands

Commands:
  usage         show this message
  env           show environment variables
  pwd           show the current working directory

Functions:
  sleep         time.sleep wrapper

Objects:
  g             Galileo object that allows you to interact with the system
  show          Prints runtime information about the system to system out
  rtbl          Symmetry routing table

Type help(<function>) or help(<object>) to learn how to use the functions.
''')


def sleep(secs: float):
    """
    Delay execution for a given number of seconds. The argument may be a floating point number for subsecond precision.
    :param secs: seconds to sleep
    :return: None
    """
    time.sleep(secs)


@Stringer
def env():
    return dict(os.environ)


@Stringer
def pwd():
    return os.path.abspath(os.curdir)


class ClientGroup:
    """
    Allows the interaction with a set of galileo clients. Functions like `rps`, `close` operate on all clients in the
    ClientGroup.
    """

    ctrl: ClusterController
    clients: List[ClientDescription]

    def __init__(self, ctrl, clients, cfg=None) -> None:
        super().__init__()
        self.ctrl = ctrl
        self.clients: List[ClientDescription] = clients
        self.cfg = cfg

    def rps(self, n: float):
        """
        Set the request generation rate of all clients in the group.
        :param n: requests per second (can be fractional, e.g. 0.5 to send a request every 2 seconds)
        """
        for c in self.clients:
            self.ctrl.set_rps(c.client_id, n)

    def add(self, n=1):
        """
        Add n number of clients with the same configuration to this ClientGroup
        :param n: the number of clients
        :return: a client group containing only the clients that were added
        """
        if self.cfg is None:
            raise ValueError('need config to add clients to group')

        new_clients = self.ctrl.create_clients(self.cfg, n)
        self.clients.extend(new_clients)
        return ClientGroup(self.ctrl, new_clients, self.cfg)

    def close(self, n=None):
        """
        Close all or a specific number of clients in the client group. Clients are terminated remotely.

        :param n: the number of clients to terminate (all if None)
        :return: the ids of the clients that were closed
        """
        if n is None:
            n = len(self.clients)

        print('closing %d clients' % n)

        removed = list()
        for _ in range(n):
            removed.append(self.clients.pop())

        for c in removed:
            pymq.publish(CloseClientCommand(c.client_id))

        return [description.client_id for description in removed]

    def __repr__(self) -> str:
        if not self.clients:
            return 'empty client group'

        return '\n'.join([c.client_id for c in self.clients])


class Galileo:
    ctrl: ClusterController = None

    def __init__(self, ctrl) -> None:
        super().__init__()
        self.ctrl = ctrl

    def start_tracing(self):
        """
        Send a StartTracing command to all workers.
        :return: the number of workers who received the command
        """
        return self.ctrl.start_tracing()

    def stop_tracing(self):
        """
        Send a StopTracing command to all workers.
        :return: the number of workers who received the command
        """
        return self.ctrl.stop_tracing()

    def workers(self) -> List[str]:
        """
        List registered workers.
        :return: a list of strings
        """
        return self.ctrl.list_workers()

    def ping(self):
        """
        Send a synchronous ping to all workers and return the response. May contain error tuples.
        :return:
        """
        return self.ctrl.ping()

    def discover(self):
        """
        Send a discover command to all workers, which tells them to re-register to redis.
        :return: the number of workers who received the command
        """
        return self.ctrl.discover()

    def clients(self, *client_ids) -> ClientGroup:
        """
        Returns a ClientGroup for the given client_ids, or all clients of no client_ids are specified.
        :param client_ids: optional variadic client_ids
        :return: a ClientGroup
        """
        clients = self.ctrl.list_clients()

        if client_ids:
            clients = [c for c in clients if c.client_id in client_ids]

        return ClientGroup(self.ctrl, clients)

    def spawn(self, service, num: int = 1, client: str = None, client_parameters: dict = None) -> ClientGroup:
        """
        Spawn clients for the given service and distribute them across workers.

        :param service: the service name
        :param num: the number of clients
        :param client: the client app name (optional, if not given will use service name)
        :param client_parameters: parameters for the app (optional, e.g.: '{ "size": "small" }'
        :return a new ClientGroup for the created clients
        """
        cfg = ClientConfig(service, client=client, parameters=client_parameters)
        clients = self.ctrl.create_clients(cfg, num)
        return ClientGroup(self.ctrl, clients, cfg)


class Show:
    g: Galileo

    def __init__(self, gal: Galileo) -> None:
        super().__init__()
        self.g = gal

    def workers(self):
        workers = self.g.workers()
        if workers:
            return Stringer(workers)
        else:
            return Stringer('no available workers')

    def clients(self):
        cs = self.g.clients().clients
        data = [c._asdict() for c in cs]
        print_tabular(data)


class RoutingTableHelper:
    """
    View or update the symmetry RoutingTable to control where galileo clients send their requests.
    """
    table: RoutingTable

    def __init__(self, table) -> None:
        super().__init__()
        self.table = table

    def record(self, service):
        """
        Get the RoutingRecord for a specific service.
        :param service: the service
        :return: the routing record, or None
        """
        try:
            return self.table.get_routing(service)
        except ValueError:
            return None

    def records(self):
        """
        Return all routing records
        :return: a list of RoutingRecord tuples
        """
        return [self.table.get_routing(service) for service in self.table.list_services()]

    def set(self, service: str, hosts: List[str], weights: List[float] = None):
        """
        Creates a new or overwrites an existing RoutingRecord
        :param service: the service
        :param hosts: a list of hosts
        :param weights: an optional list of weights for the hosts
        :return:
        """
        if weights is None:
            weights = [1] * len(hosts)

        record = RoutingRecord(service, hosts, weights)
        self.table.set_routing(record)
        return record

    def update_weights(self, service, weights: List[float]):
        """
        Update the weights for the routing record of the given service. raises a ValueError if the record does not
        exist, or if the number of weights does not match the number of hosts in the record.

        :param service: the service
        :param weights: the updated weights
        :return:
        """
        record = self.table.get_routing(service)

        if len(weights) != len(record.weights):
            raise ValueError('invalid number of weights')

        record.weights.clear()
        record.weights.extend(weights)

        self.table.set_routing(record)

        return self

    def append(self, service: str, host: str, weight: float = 1):
        """
        Adds a single host and optional weight to the routing record of the services. If the record does not exist, it
        is created.
        :param service: the service
        :param host: the host
        :param weight: the weight
        :return:
        """
        try:
            record = self.table.get_routing(service)
        except ValueError:
            return self.set(service, [host], [weight])

        record.hosts.append(host)
        record.weights.append(weight)
        self.table.set_routing(record)

        return self

    def remove(self, service: str):
        """
        Removes the routing record of the given service.
        :param service: the service
        :return: this object
        """
        self.table.remove_service(service)
        return self

    def clear(self):
        """
        Removes all routing records from the table.
        :return: this object
        """
        self.table.clear()
        return self

    def print(self):
        print(self.__repr__())

    def __repr__(self):
        return sprint_routing_table(self.table)


is_interactive = sys.__stdin__.isatty()


def init(rds) -> Dict[str, object]:
    eventbus = pymq.init(RedisConfig(rds))

    g = Galileo(RedisClusterController(rds))
    show = Show(g)
    rtbl = RoutingTableHelper(RedisRoutingTable(rds))

    return {
        'g': g,
        'show': show,
        'rtbl': rtbl,
        'eventbus': eventbus,
    }


def init_module(rds, name=None):
    gvars = init(rds)

    import sys
    if name is None:
        name = __name__

    module = sys.modules[name]

    for name, value in gvars.items():
        setattr(module, name, value)

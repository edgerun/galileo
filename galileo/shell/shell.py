import io
import os
import sys
import time
from typing import List, Dict

import pymq
from pymq.provider.redis import RedisConfig
from symmetry.api import RoutingRecord, RoutingTable
from symmetry.routing import RedisRoutingTable

from galileo.controller.cluster import ClusterController, RedisClusterController
from galileo.worker.api import ClientConfig, ClientDescription, SetRpsCommand, CloseClientCommand

prompt = 'galileo> '

banner = r"""
                                   __  __
 .-.,="``"=.          ____ _____ _/ (_) /__  ____
 '=/_       \        / __ `/ __ `/ / / / _ \/ __ \
  |  '=._    |      / /_/ / /_/ / / / /  __/ /_/ /
   \     `=./`.     \__, /\__,_/_/_/_/\___/\____/
    '=.__.=' `='   /____/

"""

usage = '''the galileo shell is an interactive python shell that provides the following commands

Commands:
  usage         show this message

Functions:
  sleep         time.sleep wrapper

Objects:
  g             Galileo object that allows you to interact with the system
  show          Prints runtime information about the system to system out
  rtbl          Symmetry routing table

Type help(<function>) or help(<object>) to learn how to use the functions.
'''


class ClientGroup:
    ctrl: ClusterController
    clients: List[ClientDescription]

    def __init__(self, ctrl, clients, cfg=None) -> None:
        super().__init__()
        self.ctrl = ctrl
        self.clients: List[ClientDescription] = clients
        self.cfg = cfg

    def rps(self, n):
        for c in self.clients:
            pymq.publish(SetRpsCommand(c.client_id, n))

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
        return self.ctrl.start_tracing()

    def stop_tracing(self):
        return self.ctrl.stop_tracing()

    def workers(self):
        return self.ctrl.list_workers()

    def ping(self):
        return self.ctrl.ping()

    def discover(self):
        return self.ctrl.discover()

    def clients(self, *client_ids) -> ClientGroup:
        clients = self.ctrl.list_clients()

        if client_ids:
            clients = [c for c in clients if c.client_id in client_ids]

        return ClientGroup(self.ctrl, clients)

    def spawn(self, service, num: int = 1, client: str = None, client_parameters: dict = None) -> ClientGroup:
        """
        Spawn a new client for the given service on the given worker.

        :param service: the service name
        :param num: the number of clients
        :param client: the client app name (optional, if not given will use service name)
        :param client_parameters: parameters for the app (optional, e.g.: '{ "size": "small" }'
        """

        # TODO: get available workers, distribute clients evenly across workers

        cfg = ClientConfig(service, client=client, parameters=client_parameters)
        clients = self.ctrl.create_clients(cfg, num)
        return ClientGroup(self.ctrl, clients, cfg)


class Show:
    g: Galileo

    def __init__(self, gal: Galileo) -> None:
        super().__init__()
        self.g = gal

    def workers(self):
        for w in self.g.workers():
            print(w)

    def clients(self):
        cs = self.g.clients().clients
        data = [c._asdict() for c in cs]
        print_tabular(data)

    def env(self):
        for k, v in os.environ.items():
            print(f'{k} = {v}')


class RoutingTableHelper:
    table: RoutingTable

    def __init__(self, table) -> None:
        super().__init__()
        self.table = table

    def record(self, service):
        return self.table.get_routing(service)

    def records(self):
        return [self.table.get_routing(service) for service in self.table.list_services()]

    def set(self, service: str, hosts: List[str], weights: List[float]):
        record = RoutingRecord(service, hosts, weights)
        self.table.set_routing(record)
        return record

    def update_weights(self, service, weights: List[float]):
        record = self.table.get_routing(service)

        if len(weights) != len(record.weights):
            raise ValueError('invalid number of weights')

        record.weights.clear()
        record.weights.extend(weights)

        self.table.set_routing(record)

        return self

    def append(self, service: str, host: str, weight: float):
        try:
            record = self.table.get_routing(service)
        except ValueError:
            return self.set(service, [host], [weight])

        record.hosts.append(host)
        record.weights.append(weight)
        self.table.set_routing(record)

        return self

    def remove(self, service: str):
        self.table.remove_service(service)
        return self

    def clear(self):
        self.table.clear()
        return self

    def print(self):
        print(self.dumps(self.table))

    def __repr__(self):
        return self.dumps(self.table)

    @staticmethod
    def dumps(table):
        records = [table.get_routing(service) for service in table.list_services()]
        output = io.StringIO()

        w = [-25, 20, 9]  # TODO: read from records

        sep = ['-' * abs(i) for i in w]
        sep = '+-' + '-+-'.join(sep) + '-+'

        row_fmt = ['%%%ds' % w[i] for i in range(len(w))]
        row_fmt = '| ' + ' | '.join(row_fmt) + ' |'

        header = ('Service', 'Hosts', 'Weights')

        print(sep, file=output)
        print(row_fmt % header, file=output)
        print(sep, file=output)

        for record in records:
            for i in range(len(record.hosts)):
                ls = (record.service if i == 0 else '', record.hosts[i], record.weights[i])
                print(row_fmt % ls, file=output)
            print(sep, file=output)

        with output:
            return output.getvalue().strip()


def sleep(secs: float):
    """
    Delay execution for a given number of seconds. The argument may be a floating point number for subsecond precision.
    :param secs: seconds to sleep
    :return: None
    """
    time.sleep(secs)


def print_tabular(data, columns=None, widths=None, printer=None):
    if not data and not columns:
        return

    printer = printer or print
    columns = columns or data[0].keys()
    if not widths:
        widths = list()
        for c in columns:
            max_len = len(c)

            for row in data:
                max_len = max(max_len, len(str(row[c])))

            widths.append(-max_len)

    sep = ['-' * abs(i) for i in widths]
    sep = '+-' + '-+-'.join(sep) + '-+'

    row_fmt = ['%%%ds' % widths[i] for i in range(len(widths))]
    row_fmt = '| ' + ' | '.join(row_fmt) + ' |'

    header = tuple(columns)

    printer(sep)
    printer(row_fmt % header)
    printer(sep)

    for record in data:
        row = tuple([record[k] for k in columns])
        printer(row_fmt % row)

    printer(sep)


is_interactive = sys.__stdin__.isatty()


def init(rds) -> Dict[str, object]:
    pymq.init(RedisConfig(rds))

    g = Galileo(RedisClusterController(rds))
    show = Show(g)
    rtbl = RoutingTableHelper(RedisRoutingTable(rds))

    return {
        'g': g,
        'show': show,
        'rtbl': rtbl,
    }


def init_module(rds, name=None):
    gvars = init(rds)

    import sys
    if name is None:
        name = __name__

    module = sys.modules[name]

    for name, value in gvars.items():
        setattr(module, name, value)

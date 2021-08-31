import atexit
import multiprocessing
import os
import sys
import time
from threading import Thread, Condition
from typing import List, Dict, NamedTuple, Set, Tuple

import pymq
from galileodb.cli.recorder import run as run_recorder
from galileodb.model import Event as ExperimentEvent
from galileodb.reporter.events import RedisEventReporter as ExperimentEventReporter
from pymq.provider.redis import RedisConfig
from telemc import TelemetryController

from galileo.controller.cluster import ClusterController, RedisClusterController
from galileo.routing import RoutingRecord, RoutingTable, RedisRoutingTable
from galileo.shell.printer import sprint_routing_table, print_tabular, Stringer
from galileo.worker.api import ClientConfig, ClientDescription, CloseClientCommand, ClientInfo, WorkloadDoneEvent
from galileo.worker.client import single_request

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
  exp           Galileo experiment
  rtbl          Symmetry routing table
  telemd        Telemd object to pause, unpause and list registered telemd daemons

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


class RequestFuture:
    ctrl: ClusterController
    client_ids: Set[str]

    def __init__(self, ctrl, client_ids) -> None:
        super().__init__()
        self.ctrl = ctrl
        self.client_ids = client_ids
        self.done = False
        self.aborted = False
        self.lock = Condition()

    def run(self, n=None, ia=None):
        clients_done = set(self.client_ids)

        # lots of problems with this unfortunately, may never terminate if clients disappear, concurrent events from
        # previous (aborted) calls will interfere with future calls, etc.

        def done_subscriber(event: WorkloadDoneEvent):
            clients_done.remove(event.client_id)
            if len(clients_done) == 0:
                with self.lock:
                    self.done = True
                    self.lock.notify_all()

        try:
            with self.lock:
                pymq.subscribe(done_subscriber)
                for c in self.client_ids:
                    self.ctrl.set_workload(c, ia, n)

                self.lock.wait_for(self.stopped)
        finally:
            pymq.unsubscribe(done_subscriber)

    def stopped(self):
        return self.done or self.aborted

    def abort(self):
        with self.lock:
            self.aborted = True
            self.lock.notify_all()

    def wait(self, timeout=None, abort_after_timeout=True):
        with self.lock:
            result = self.lock.wait_for(self.stopped, timeout=timeout)

        if not result and abort_after_timeout:
            self.abort()  # make sure run terminates as well


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

        self.running_request: RequestFuture = None

    def rps(self, n: float):
        """
        Set the request generation rate of all clients in the group.
        :param n: requests per second (can be fractional, e.g. 0.5 to send a request every 2 seconds)
        """
        if n == 0:
            self.pause()
        else:
            self.request(ia=(1 / n))

    def request(self, n=None, ia=None) -> RequestFuture:
        """
        Tell the clients in the group to start generating requests. You can specify a message rate, or a number of
        requests, or both.

        The interarrival can be specified either as int/float, then it is interpreted as constant interarrival. The
        following example causes clients to send 5 message per second::

            c.request(ia=0.2)

        It can also be specified as a tuple, where the first element specifies the distribution used from ``random``:
        ``random.<distribution>``, and the remaining elements specify the arguments that are passed to the call::

            c.requests(ia=('expovariate', 1))

        Uses ``random.expovariate(1)`` to generate interarrivals.

        The messages limit can be used with or without the ``ia`` parameter::

            c.requests(n=100)

        will send 100 messages as fast as possible (clients currently work synchronously). Whereas::

            c.requests(n=100, ia=0.2)

        Will send 100 messages but pause for 0.2 between each message.

        The method returns a RequestFuture on which you can call ``wait()`` if you want to block until the clients are
        done.

            c.request(n=100).wait()

        :param n: the maximum number of requests
        :param ia: the request interarrival
        :return a RequestFuture object
        """

        # if a previous request is running, abort the future to unsubscribe from events properly
        if self.running_request and not self.running_request.stopped():
            self.running_request.abort()
            self.running_request.wait(1)

        future = RequestFuture(self.ctrl, {c.client_id for c in self.clients})
        t = Thread(target=future.run, args=(n, ia))
        t.start()

        self.running_request = future

        return future

    def pause(self):
        """
        Pause the current workload set by ``ClientGroup.request``.
        """
        for c in self.clients:
            self.ctrl.stop_workload(c.client_id)

    def info(self) -> List[ClientInfo]:
        return pymq.stub('Client.get_info', timeout=2, multi=True)()

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

    def __add__(self, other) -> 'ClientGroup':
        return ClientGroup.merge(self, other)

    @staticmethod
    def merge(c1: 'ClientGroup', c2: 'ClientGroup') -> 'ClientGroup':
        if c1.ctrl is not c2.ctrl:
            raise ValueError('client groups have different controllers')

        clients = list()
        clients.extend(c1.clients)
        clients.extend(c2.clients)

        return ClientGroup(c1.ctrl, clients)


class Telemd:
    telemd_ctrl: TelemetryController = None

    def __init__(self, telemd_ctrl) -> None:
        super().__init__()
        self.telemd_ctrl = telemd_ctrl

    def start_telemd(self, hosts: List[str] = None):
        """
        Send a unpause message to all registered telemd hosts
        """
        if hosts is not None:
            for host in hosts:
                self.telemd_ctrl.unpause(host)
        else:
            self.telemd_ctrl.unpause_all()

    def stop_telemd(self, hosts: List[str] = None):
        """
        Send a pause message to all registered telemd hosts
        """
        if hosts is not None:
            for host in hosts:
                self.telemd_ctrl.pause(host)
        else:
            self.telemd_ctrl.pause_all()

    def list_telemd_hosts(self):
        """List all registered telemd hosts"""
        return self.telemd_ctrl.get_nodes()


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

    def workers_info(self) -> List[Tuple[str, str]]:
        return self.ctrl.list_workers_info()

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

    def request(self, service, client: str = None, parameters: dict = None, router_type='SymmetryHostRouter',
                worker_labels: dict = None):
        """
        Send a request with the given configuration like a client would. See ``spawn`` for the parameters. An additional
        parameter is the ``router_type`` which specifies which router to use (see `Context.create_router`)
        """
        cfg = ClientConfig(service, client=client, parameters=parameters, worker_labels=worker_labels)
        resp = single_request(cfg, router_type=router_type)

        return resp

    def spawn(self, service, num: int = 1, client: str = None, parameters: dict = None,
              worker_labels: dict = None) -> ClientGroup:
        """
        Spawn clients for the given service and distribute them across workers. If no client app is specified, a default
        http client will be created that creates http requests from the (optional) parameters::

            spawn('myservice', parameters={'method': 'get', 'path': '/', 'kwargs': None}

        is equivalent to::

            spawn('myservice')

        Another example::

            spawn('myservice', 2, parameters={'method': 'post', 'path': '/', 'kwargs': {'data': 'my post data'}})

        will result is POST requests to the path '/' where the 'kwargs' dict is passed to the python
        ``requests.request`` call as keyword arguments.

        :param service: the service name
        :param num: the number of clients
        :param client: the client app name (optional, if not given will use service name)
        :param parameters: parameters for the app (optional, e.g.: '{ "size": "small" }'
        :param worker_labels: labels that workers must match to be part of the group
        :return a new ClientGroup for the created clients
        """
        cfg = ClientConfig(service, client=client, parameters=parameters, worker_labels=worker_labels)
        clients = self.ctrl.create_clients(cfg, num)
        return ClientGroup(self.ctrl, clients, cfg)


class ExperimentArguments(NamedTuple):
    name: str = None
    creator: str = None


class Experiment:
    event_reporter: ExperimentEventReporter

    def __init__(self, rds) -> None:
        super().__init__()
        self.event_reporter = ExperimentEventReporter(rds)
        self.experiment = None
        self._atexit = False

    def event(self, name: str, value: str = None):
        """
        Sends a galileo experiment event.

        :param name: the event name
        :param value: the optional event value
        """
        ts = time.time()
        self.event_reporter.report(ExperimentEvent(ts, name, value))
        if value:
            print(f'%.3f: %s = %s' % (ts, name, value))
        else:
            print(f'%.3f: %s' % (ts, name))

    def start(self, name=None, creator=None):
        if self.experiment is not None:
            raise ValueError('experiment already running')

        if not self._atexit:
            self._atexit = True
            atexit.register(self.stop)

        args = ExperimentArguments(name, creator)

        # FIXME: i don't really like to re-use the cli module, but it was the easiest to get it working. plus we have
        #  the experiment daemon, experiment runner, experiment recorder, ...
        self.experiment = multiprocessing.Process(target=run_recorder, args=(args,), daemon=True)
        self.experiment.start()

        print('experiment started')

    def stop(self, wait=5):
        if self.experiment is None:
            return

        try:
            self.experiment.terminate()
            print('waiting for experiment to end...')
            self.experiment.join(wait)
            print('ok')
        finally:
            self.experiment = None


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

    def info(self, **exclude):
        """
        Print tabular info about the currently running clients.
        :param exclude: kwargs that exclude fields, e.g., parameters=False to hide the parameter column
        """
        data = []
        for info in self.g.clients().info():

            param_str = str(info.description.config.parameters)
            if len(param_str) > 80:
                param_str = param_str[:75] + ' ...}'

            record = {
                'client id': info.description.client_id,
                'worker': info.description.worker,
                'service': info.description.config.service,
                'client': info.description.config.client or 'default',
                'parameters': param_str,
                'requests': info.requests,
                'failed': info.failed,
            }

            for k, v in exclude.items():
                if k in record and v is False:
                    del record[k]

            data.append(record)

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
    exp = Experiment(rds)
    telemd = Telemd(TelemetryController(rds))

    return {
        'g': g,
        'show': show,
        'rtbl': rtbl,
        'exp': exp,
        'eventbus': eventbus,
        'telemd': telemd
    }


def init_module(rds, name=None):
    gvars = init(rds)

    import sys
    if name is None:
        name = __name__

    module = sys.modules[name]

    for name, value in gvars.items():
        setattr(module, name, value)

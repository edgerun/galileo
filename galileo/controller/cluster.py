import itertools
import json
import logging
import re
import sre_constants
from collections import Counter
from typing import List, Optional, Dict, Tuple

import pymq
from pymq.typing import deep_from_dict
from redis import Redis

from galileo.worker.api import RegisterWorkerCommand, ClientDescription, CreateClientCommand, ClientConfig, \
    StartTracingCommand, PauseTracingCommand, SetWorkloadCommand, StopWorkloadCommand

logger = logging.getLogger(__name__)


class ClusterController:

    def ping(self):
        raise NotImplementedError

    def discover(self):
        raise NotImplementedError

    def create_client(self, host: str, cfg: ClientConfig, num=1) -> List[ClientDescription]:
        raise NotImplementedError

    def create_clients(self, cfg: ClientConfig, num=1) -> List[ClientDescription]:
        raise NotImplementedError

    def register_worker(self, name: str, labels: Dict[str, str] = None):
        raise NotImplementedError

    def unregister_worker(self, name: str):
        raise NotImplementedError

    def list_workers(self, pattern: str = ''):
        raise NotImplementedError

    def list_workers_info(self, pattern: str = ''):
        raise NotImplementedError

    def register_client(self, client: ClientDescription):
        raise NotImplementedError

    def unregister_client(self, client_id: str):
        raise NotImplementedError

    def list_clients(self, worker: str = None) -> List[ClientDescription]:
        raise NotImplementedError

    def get_client_description(self, client_id: str) -> Optional[ClientDescription]:
        raise NotImplementedError

    def start_tracing(self):
        raise NotImplementedError

    def stop_tracing(self):
        raise NotImplementedError

    def set_workload(self, client_id, ia=None, n: int = None):
        raise NotImplementedError

    def stop_workload(self, client_id):
        raise NotImplementedError


def pack(n, workers, nr_clients):
    """
    Takes an input a list of workers, and a list of the current number of clients on each worker (same order). Returns a
    dictionary {worker: nr}, where nr is the number of clients that should be spawned on the worker.

    :param n: the number of new clients to distribute
    :param workers: the list of workers
    :param nr_clients: the number of current clients on each worker
    :return: a dictionary {worker: nr}
    """

    def packer():
        cur = list(nr_clients)

        while True:
            index_min = min(range(len(cur)), key=cur.__getitem__)
            cur[index_min] += 1
            yield workers[index_min]

    target_workers = list(itertools.islice(packer(), n))
    return dict(Counter(target_workers))


class RedisClusterController(ClusterController):
    worker_key = 'galileo:workers'
    worker_clients_key = 'galileo:worker:%s:clients'
    client_key = 'galileo:client:%s'

    def __init__(self, rds, eventbus=None) -> None:
        super().__init__()
        self.rds = rds
        self.eventbus = eventbus or pymq

    def ping(self):
        stub = self.eventbus.stub('WorkerDaemon.ping', multi=True, timeout=2)
        return stub()

    def discover(self):
        for worker in self.list_workers():
            self.rds.delete(self.worker_clients_key % worker)

        self.rds.delete(self.worker_key)
        return self.eventbus.publish(RegisterWorkerCommand())

    def register_worker(self, name: str, labels: Dict[str, str] = None):
        logger.info('registering worker %s', name)
        self.rds.sadd(self.worker_key, name)
        if labels is not None:
            self.rds.hmset(name, labels)

    def unregister_worker(self, name: str):
        logger.info('unregistering worker %s', name)
        self.rds.srem(self.worker_key, name)
        self.rds.delete(self.worker_clients_key % name)

    def list_workers(self, pattern: str = ''):
        workers = self.rds.smembers(self.worker_key)

        if not pattern:
            return workers

        try:
            return [worker for worker in workers if re.search('^%s$' % pattern, worker)]
        except sre_constants.error as e:
            raise ValueError('Invalid pattern %s: %s' % (pattern, e))

    def list_workers_info(self, pattern: str = '') -> List[Tuple[str, Dict[str, str]]]:
        workers = self.list_workers(pattern)
        items = []
        for worker in workers:
            data = self.rds.hgetall(worker)
            items.append((worker, data))
        return items

    def create_client(self, host: str, cfg: ClientConfig, num=1) -> List[ClientDescription]:
        cmd = CreateClientCommand(host, cfg, num)
        stub = self.eventbus.stub(f'WorkerDaemon.create_client:{host}', timeout=3)

        result = stub(cmd)
        # TODO: error handling
        return [deep_from_dict(d, ClientDescription) for d in result]

    def create_clients(self, cfg: ClientConfig, num=1) -> List[ClientDescription]:
        worker_client_count = self.count_worker_clients(cfg.worker_labels)
        workers = list(worker_client_count.keys())

        nr_clients = list(worker_client_count.values())

        schedule = pack(num, workers, nr_clients)

        clients = list()
        for worker, nr in schedule.items():
            created = self.create_client(worker, cfg, nr)
            clients.extend(created)

        return clients

    def register_client(self, client: ClientDescription):
        # add the client_id to the worker's clients
        worker_clients_key = self.worker_clients_key % client.worker
        self.rds.sadd(worker_clients_key, client.client_id)

        # set the client description
        client_key = self.client_key % client.client_id
        self.rds.set(client_key, serialize_client_description(client))

    def unregister_client(self, client_id: str):
        client = self.get_client_description(client_id)

        if not client:
            return

        # remove the client description
        client_key = self.client_key % client_id
        self.rds.delete(client_key)

        # remove client_id from the worker's clients
        worker_clients_key = self.worker_clients_key % client.worker
        self.rds.srem(worker_clients_key, client.client_id)

    def list_clients(self, worker: str = None) -> List[ClientDescription]:
        # TODO: error handling ¯\_(ツ)_/¯

        rds: Redis = self.rds

        if worker is not None:
            client_ids = rds.smembers(self.worker_clients_key % worker)
        else:
            # first get the keys that holds the client ids hosted on the worker
            keys = set(rds.scan_iter(self.worker_clients_key % '*'))
            # the union of those sets contains all client_ids we're looking for
            if not keys:
                return []

            client_ids = rds.sunion(keys)

        if not client_ids:
            return []

        client_keys = [self.client_key % client_id for client_id in client_ids]
        docs = rds.mget(client_keys)

        descriptions = [deserialize_client_description(doc) for doc in docs if doc is not None]

        return descriptions

    def get_client_description(self, client_id: str) -> Optional[ClientDescription]:
        key = self.client_key % client_id
        doc = self.rds.get(key)

        if doc is None:
            return None

        return deserialize_client_description(doc)

    def start_tracing(self):
        return self.eventbus.publish(StartTracingCommand())

    def stop_tracing(self):
        return self.eventbus.publish(PauseTracingCommand())

    def set_workload(self, client_id, ia=None, n: int = None):
        if ia is None and n is None:
            raise ValueError('need interarrival or number of messages')

        dist, params = 'constant', None

        if isinstance(ia, (int, float)):
            dist, params = 'constant', (ia,)
        elif isinstance(ia, tuple):
            dist, params = ia[0], ia[1:]

        cmd = SetWorkloadCommand(client_id, num=n, distribution=dist, parameters=params)
        return self.eventbus.publish(cmd)

    def stop_workload(self, client_id):
        return self.eventbus.publish(StopWorkloadCommand(client_id))

    def count_worker_clients(self, worker_labels: Dict[str, str] = None):
        workers_labels = self.list_workers_info()
        workers = list(map(lambda x: x[0], workers_labels))
        if worker_labels is not None:
            for worker, labels in workers_labels:
                for k, v in worker_labels.items():
                    if labels[k] != v:
                        workers.remove(worker)
                        break

        if len(workers) == 0:
            raise IndexError('No workers found that match labels.')

        pipe = self.rds.pipeline()
        for worker in workers:
            pipe.scard(self.worker_clients_key % worker)

        nr_clients = pipe.execute()
        return dict(zip(workers, nr_clients))


def serialize_client_description(obj: ClientDescription):
    return json.dumps(obj)


def deserialize_client_description(doc: str):
    return deep_from_dict(json.loads(doc), cls=ClientDescription)

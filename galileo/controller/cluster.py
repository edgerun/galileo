import json
import logging
import re
import sre_constants
from typing import List, Optional

import pymq
from pymq.typing import deep_from_dict
from redis import Redis

from galileo.worker.api import RegisterWorkerCommand, ClientDescription, CreateClientCommand, ClientConfig, \
    StartTracingCommand, PauseTracingCommand, SetRpsCommand

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

    def register_worker(self, name: str):
        raise NotImplementedError

    def unregister_worker(self, name: str):
        raise NotImplementedError

    def list_workers(self, pattern: str = ''):
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

    def set_rps(self, client_id, n: float, dist: str = "constant", dist_args=None):
        raise NotImplementedError


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

    def register_worker(self, name: str):
        logger.info('registering worker %s', name)
        self.rds.sadd(self.worker_key, name)

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

    def create_client(self, host: str, cfg: ClientConfig, num=1) -> List[ClientDescription]:
        cmd = CreateClientCommand(host, cfg, num)
        stub = self.eventbus.stub(f'WorkerDaemon.create_client:{host}', timeout=3)

        result = stub(cmd)
        # TODO: error handling
        return result

    def create_clients(self, cfg: ClientConfig, num=1) -> List[ClientDescription]:
        # TODO: this is essentially a scheduler, improve to balance clients between workers.

        clients = list()
        workers = list(self.list_workers())

        for n in range(num):
            i = n % len(workers)
            worker = workers[i]

            created = self.create_client(worker, cfg, 1)
            clients.extend([deep_from_dict(d, ClientDescription) for d in created])

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

        descriptions = [deserialize_client_description(doc) for doc in docs]

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

    def set_rps(self, client_id, n: float, dist="constant", dist_args=None):
        return self.eventbus.publish(SetRpsCommand(client_id, n, dist, dist_args))


def serialize_client_description(obj: ClientDescription):
    return json.dumps(obj)


def deserialize_client_description(doc: str):
    return deep_from_dict(json.loads(doc), cls=ClientDescription)

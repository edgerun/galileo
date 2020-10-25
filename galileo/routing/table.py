import abc
import logging
import threading
from typing import NamedTuple, List

import redis

logger = logging.getLogger(__name__)


class RoutingRecord(NamedTuple):
    service: str
    hosts: List[str]
    weights: List[float]


class RoutingTable(abc.ABC):
    def get_routing(self, service) -> RoutingRecord:
        raise NotImplementedError

    def set_routing(self, record: RoutingRecord):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    def list_services(self):
        raise NotImplementedError

    def remove_service(self, service):
        raise NotImplementedError

    def get_routes(self):
        return [self.get_routing(service) for service in self.list_services()]


class RedisRoutingTable(RoutingTable):
    update_channel = 'routing:updates'

    def __init__(self, rds) -> None:
        super().__init__()
        self.rds = rds

    def list_services(self):
        return self.rds.smembers('routing:services')

    def get_routing(self, service) -> RoutingRecord:
        rds = self.rds.pipeline()
        rds.lrange('routing:hosts:%s' % service, 0, -1)
        rds.lrange('routing:weights:%s' % service, 0, -1)
        result = rds.execute()

        if result[0]:
            return RoutingRecord(service, result[0], [float(i) for i in result[1]])

        raise ValueError(f"No routing record found for service '{service}'")

    def set_routing(self, record: RoutingRecord):
        if len(record.weights) != len(record.hosts):
            raise ValueError('The number of weights does not match the population')

        rds = self.rds.pipeline()
        rds.delete('routing:hosts:%s' % record.service)
        rds.delete('routing:weights:%s' % record.service)

        rds.sadd('routing:services', record.service)
        rds.rpush('routing:hosts:%s' % record.service, *record.hosts)
        rds.rpush('routing:weights:%s' % record.service, *record.weights)
        rds.publish(self.update_channel, record.service)

        rds.execute()

    def remove_service(self, service):
        self.remove(service)

    def clear(self):
        rds = self.rds.pipeline()
        for service in self.list_services():
            rds.delete('routing:hosts:%s' % service)
            rds.delete('routing:weights:%s' % service)
            rds.publish(self.update_channel, service)
        rds.delete('routing:services')
        rds.execute()

    def remove(self, service):
        rds = self.rds.pipeline()
        rds.delete('routing:hosts:%s' % service)
        rds.delete('routing:weights:%s' % service)
        rds.srem('routing:services', service)
        rds.publish(self.update_channel, service)
        rds.execute()


class ReadOnlyListeningRedisRoutingTable(RoutingTable):

    def __init__(self, rds) -> None:
        super().__init__()
        self.rds = rds
        self.rtable = RedisRoutingTable(rds)
        self._cache = dict()
        self._services = list()

        self._reload_lock = threading.Lock()

        self._pubsub = None
        self._thread = threading.Thread(target=self.listen)

    def start(self):
        self._thread.start()

    def stop(self, timeout=None):
        self.close()
        self._thread.join(timeout)

    def listen(self):
        self._pubsub = self.rds.pubsub()

        try:
            self._pubsub.subscribe(self.rtable.update_channel)

            with self._reload_lock:
                self._services = self.rtable.list_services()

            for item in self._pubsub.listen():
                if item['type'] == 'unsubscribe':
                    break
                if item['type'] != 'message':
                    continue

                service = item['data']

                logger.debug('received routing table update for %s', service)

                with self._reload_lock:
                    if service in self._cache:
                        del self._cache[service]
                    self._services = self.rtable.list_services()
        except redis.ConnectionError:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception('listener terminated due to connection error')
            else:
                logger.error('listener terminated due to connection error')
        finally:
            self._pubsub.close()

    def close(self):
        try:
            self._pubsub.unsubscribe()
        except redis.ConnectionError:
            # fail silently if connection is already closed
            pass

    def list_services(self):
        return self._services

    def get_routing(self, service) -> RoutingRecord:
        record = self._cache.get(service, None)

        if record is not None:
            return record

        with self._reload_lock:
            record = self.rtable.get_routing(service)
            self._cache[service] = record
            logger.debug('loaded routing record into cache %s', record)
            return record

    def set_routing(self, record: RoutingRecord):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    def remove_service(self, service):
        raise NotImplementedError

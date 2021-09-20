import atexit
import logging
import os
import time
from socket import gethostname
from typing import MutableMapping, List, Dict

import redis
import requests
from galileodb import ExperimentDatabase
from galileodb.factory import create_experiment_database_from_env
from galileodb.trace import TraceLogger, TraceWriter, FileTraceWriter, RedisTopicTraceWriter, DatabaseTraceWriter

from galileo.apps.loader import AppClientLoader, AppClientDirectoryLoader, AppRepositoryFallbackLoader
from galileo.apps.repository import RepositoryClient
from galileo.routing import Router, ServiceRequest, ServiceRouter, HostRouter, StaticRouter, RedisRoutingTable, \
    ReadOnlyListeningRedisRoutingTable, WeightedRoundRobinBalancer

logger = logging.getLogger(__name__)


class Context:
    """
    Factory for various worker services. Below are the environment variables that can be set:

    - Logging
        - galileo_log_level (DEBUG|INFO|WARN| ... )

    - Redis connection:
        - galileo_redis_host (localhost)
        - galileo_redis_port (6379)

    - Trace logging:
        - galileo_trace_logging: file|redis|sql
        - mysql:
            - galileo_expdb_driver: sqlite|mysql
            - sqlite:
                - galileo_expdb_sqlite_path ('/tmp/galileo_sqlite')
            - mysql:
                - galileo_expdb_mysql_host (localhost)
                - galileo_expdb_mysql_port (3307)
                - galileo_expdb_mysql_user
                - galileo_expdb_mysql_password
                - galileo_expdb_mysql_db

    - Request router
        - galileo_router_type: SymmetryServiceRouter|SymmetryHostRouter|StaticRouter|DebugRouter
            - StaticRouter:
                - galileo_router_static_host (http://localhost)

    - Client app loader:
        - galileo_apps_dir ('./apps')
        - galileo_apps_repository ('http://localhost:5001')
    """

    def __init__(self, env: MutableMapping = os.environ) -> None:
        super().__init__()
        self.env = env

    def getenv(self, *args, **kwargs):
        return self.env.get(*args, **kwargs)

    def keys(self, prefix: str = 'galileo_') -> List[str]:
        if prefix is None:
            return list(self.env.keys())
        else:
            return list(filter(lambda x: x.startswith('galileo_'), self.env.keys()))

    def items(self, prefix: str = 'galileo_') -> Dict[str, str]:
        if prefix is None:
            return dict(self.env.values())
        else:
            values = {}
            keys = self.keys(prefix)
            for key in keys:
                value = self.getenv(key)
                values[key] = value
        return values

    @property
    def worker_name(self):
        return self.env.get('galileo_worker_name', gethostname())

    def create_trace_writer(self) -> TraceWriter:
        trace_logging = self.env.get('galileo_trace_logging')
        logger.debug('trace logging: %s', trace_logging or 'None')

        if not trace_logging:
            return None
        elif trace_logging == 'file':
            return FileTraceWriter(self.worker_name)
        elif trace_logging == 'redis':
            return RedisTopicTraceWriter(self.create_redis())
        elif trace_logging == 'sql':
            return DatabaseTraceWriter(self.create_exp_db())
        else:
            raise ValueError('Unknown trace logging type %s' % trace_logging)

    def create_trace_logger(self, trace_queue, start=True) -> TraceLogger:
        writer = self.create_trace_writer()
        return TraceLogger(trace_queue, writer, start)

    def create_router(self, router_type=None):
        if router_type is None:
            router_type = self.env.get('galileo_router_type', 'CachingSymmetryHostRouter')

        if router_type == 'SymmetryServiceRouter':
            rtable = RedisRoutingTable(self.create_redis())
            balancer = WeightedRoundRobinBalancer(rtable)
            return ServiceRouter(balancer)
        elif router_type == 'CachingSymmetryServiceRouter':
            rtable = ReadOnlyListeningRedisRoutingTable(self.create_redis())
            rtable.start()
            atexit.register(rtable.stop, timeout=2)
            balancer = WeightedRoundRobinBalancer(rtable)
            return ServiceRouter(balancer)
        elif router_type == 'SymmetryHostRouter':
            rtable = RedisRoutingTable(self.create_redis())
            balancer = WeightedRoundRobinBalancer(rtable)
            return HostRouter(balancer)
        elif router_type == 'CachingSymmetryHostRouter':
            rtable = ReadOnlyListeningRedisRoutingTable(self.create_redis())
            rtable.start()
            atexit.register(rtable.stop, timeout=2)
            balancer = WeightedRoundRobinBalancer(rtable)
            return HostRouter(balancer)
        elif router_type == 'StaticRouter':
            host = self.env.get('galileo_router_static_host', 'http://localhost')
            return StaticRouter(host)
        elif router_type == 'DebugRouter':
            return DebugRouter()

        raise ValueError('Unknown router type %s' % router_type)

    def create_app_loader(self) -> AppClientLoader:
        loader = AppClientDirectoryLoader(self.env.get('galileo_apps_dir', os.path.abspath('./apps')))
        repo = RepositoryClient(self.env.get('galileo_apps_repository', 'http://localhost:5001'))

        return AppRepositoryFallbackLoader(loader, repo)

    def create_redis(self) -> redis.Redis:
        host = self.env.get('galileo_redis_host', 'localhost')

        if host.startswith('file://'):
            import redislite
            f_path = host.replace('file://', '')
            return redislite.Redis(dbfilename=f_path, decode_responses=True)

        params = {
            'host': host,
            'port': int(self.env.get('galileo_redis_port', '6379')),
            'decode_responses': True,
        }
        logger.debug("establishing redis connection with params %s", params)

        return redis.Redis(**params)

    def create_exp_db(self) -> ExperimentDatabase:
        return create_experiment_database_from_env(self.env)


class DebugRouter(Router):

    def request(self, req: ServiceRequest) -> requests.Response:
        logger.debug('DebugRouter received service request %s', req)

        response = requests.Response()
        response.status_code = 200
        response.url = self._get_url(req)
        req.sent = time.time()

        return response

    def _get_url(self, req: ServiceRequest) -> str:
        return 'http://debughost' + req.path

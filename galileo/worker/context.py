import logging
import os
from socket import gethostname
from typing import MutableMapping

import redis
from symmetry.gateway import WeightedRandomBalancer, SymmetryServiceRouter, SymmetryHostRouter, StaticRouter
from symmetry.routing import ReadOnlyListeningRedisRoutingTable

from galileo.apps.loader import AppClientLoader, AppClientDirectoryLoader, AppRepositoryFallbackLoader
from galileo.apps.repository import RepositoryClient
from galileo.experiment.db import ExperimentDatabase
from galileo.experiment.db.factory import create_experiment_database_from_env
from galileo.worker.trace import TraceLogger, TraceDatabaseLogger, TraceFileLogger, TraceRedisLogger

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
        - galileo_router_type: SymmetryServiceRouter|SymmetryHostRouter|StaticRouter
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

    @property
    def worker_name(self):
        return self.env.get('galileo_worker_name', gethostname())

    def create_trace_logger(self, trace_queue) -> TraceLogger:
        trace_logging = self.env.get('galileo_trace_logging')

        logger.debug('trace logging: %s', trace_logging or 'None')

        # careful when passing state to the TraceLogger: it's a new process
        if not trace_logging:
            return TraceLogger(trace_queue)
        elif trace_logging == 'file':
            return TraceFileLogger(trace_queue, host_name=self.worker_name)
        elif trace_logging == 'redis':
            return TraceRedisLogger(trace_queue, rds=self.create_redis())
        elif trace_logging == 'sql':
            return TraceDatabaseLogger(trace_queue, experiment_db=self.create_exp_db())
        else:
            raise ValueError('Unknown trace logging type %s' % trace_logging)

    def create_router(self):
        router_type = self.env.get('galileo_router_type', 'SymmetryServiceRouter')
        rds = self.create_redis()

        if router_type == 'SymmetryServiceRouter':
            rtable = ReadOnlyListeningRedisRoutingTable(rds)
            balancer = WeightedRandomBalancer(rtable)
            return SymmetryServiceRouter(balancer)
        elif router_type == 'SymmetryHostRouter':
            rtable = ReadOnlyListeningRedisRoutingTable(rds)
            balancer = WeightedRandomBalancer(rtable)
            return SymmetryHostRouter(balancer)
        elif router_type == 'StaticRouter':
            host = self.env.get('galileo_router_static_host', 'http://localhost')
            return StaticRouter(host)

        raise ValueError('Unknown router type %s' % router_type)

    def create_app_loader(self) -> AppClientLoader:
        loader = AppClientDirectoryLoader(self.env.get('galileo_apps_dir', os.path.abspath('./apps')))
        repo = RepositoryClient(self.env.get('galileo_apps_repository', 'http://localhost:5001'))

        return AppRepositoryFallbackLoader(loader, repo)

    def create_redis(self) -> redis.Redis:
        params = {
            'host': self.env.get('galileo_redis_host', 'localhost'),
            'port': int(self.env.get('galileo_redis_port', '6379')),
            'decode_responses': True,
        }

        return redis.Redis(**params)

    def create_exp_db(self) -> ExperimentDatabase:
        return create_experiment_database_from_env(self.env)

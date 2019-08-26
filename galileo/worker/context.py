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

    - Redis connection:
        - GALILEO_REDIS_HOST (localhost)
        - GALILEO_REDIS_PORT (6379)

    - Trace logging:
        - GALILEO_TRACE_LOGGING: file|redis|mysql
        - mysql:
            - DB_TYPE: sqlite|mysql
            - sqlite:
                - SQLITE_PATH ('/tmp/galileo.sqlite')
            - mysql:
                - MYSQL_HOST (localhost)
                - MYSQL_PORT (3307)
                - MYSQL_USER
                - MYSQL_PASSWORD
                - MYSQL_DB

    - Request router
        - GALILEO_ROUTER_TYPE: SymmetryServiceRouter|SymmetryHostRouter|StaticRouter
            - StaticRouter:
                - GALILEO_ROUTER_STATIC_HOST (http://localhost)

    - Client app loader:
        - GALILEO_APP_DIR ('./apps')
        - GALILEO_APP_REPOSITORY ('http://localhost:5001')
    """

    def __init__(self, env: MutableMapping = os.environ) -> None:
        super().__init__()
        self.env = env

    @property
    def worker_name(self):
        return self.env.get('GALILEO_WORKER_NAME', gethostname())

    def create_trace_logger(self, trace_queue) -> TraceLogger:
        trace_logging = self.env.get('GALILEO_TRACE_LOGGING')

        logger.debug('trace logging: %s', trace_logging or 'None')

        # careful when passing state to the TraceLogger: it's a new process
        if not trace_logging:
            return TraceLogger(trace_queue)
        elif trace_logging == 'file':
            return TraceFileLogger(trace_queue, host_name=self.worker_name)
        elif trace_logging == 'redis':
            return TraceRedisLogger(trace_queue, rds=self.create_redis())
        elif trace_logging == 'mysql':
            return TraceDatabaseLogger(trace_queue, experiment_db=self.create_exp_db())
        else:
            raise ValueError('Unknown trace logging type %s' % trace_logging)

    def create_router(self):
        router_type = self.env.get('GALILEO_ROUTER_TYPE', 'SymmetryServiceRouter')
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
            host = self.env.get('GALILEO_ROUTER_STATIC_HOST', 'http://localhost')
            return StaticRouter(host)

        raise ValueError('Unknown router type %s' % router_type)

    def create_app_loader(self) -> AppClientLoader:
        loader = AppClientDirectoryLoader(self.env.get('GALILEO_APP_DIR', os.path.abspath('./apps')))
        repo = RepositoryClient(self.env.get('GALILEO_APP_REPOSITORY', 'http://localhost:5001'))

        return AppRepositoryFallbackLoader(loader, repo)

    def create_redis(self) -> redis.Redis:
        params = {
            'host': self.env.get('GALILEO_REDIS_HOST', 'localhost'),
            'port': int(self.env.get('GALILEO_REDIS_PORT', '6379')),
            'decode_responses': True,
        }

        return redis.Redis(**params)

    def create_exp_db(self) -> ExperimentDatabase:
        return create_experiment_database_from_env(self.env)

import argparse
import logging

import redis
import symmetry.eventbus as eventbus
from symmetry.eventbus.redis import RedisConfig
from symmetry.service.routing import RedisConnectedBalancer

from galileo.experiment.db import ExperimentDatabase
from galileo.experiment.db.sql import ExperimentSQLDatabase
from galileo.node.client import ExperimentService, ImageClassificationRequestFactory, MXNetImageClassifierService
from galileo.node.host import ExperimentHost
from galileo.node.router import ServiceRegistry, Router

log = logging.getLogger(__name__)


def init_database() -> ExperimentDatabase:
    from galileo.experiment.db.sql.mysql import MysqlAdapter
    return ExperimentSQLDatabase(MysqlAdapter.create_from_env())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--redis', metavar='URL', required=False,
                        help='Redis URL, for example: redis://[:password]@localhost:6379/0')
    parser.add_argument('--logging', required=False,
                        help='set log level (DEBUG|INFO|WARN|...) to activate logging')
    parser.add_argument('--trace-logging', required=False, default=None,
                        help='set trace logging type (file|redis|mysql)')

    args = parser.parse_args()

    if args.logging:
        logging.basicConfig(level=logging._nameToLevel[args.logging])

    if args.redis:
        rds = redis.Redis.from_url(url=args.redis, decode_responses=True)
    else:
        rds = redis.Redis(decode_responses=True)

    exp_db = None
    if args.trace_logging == 'mysql':
        exp_db = init_database()
        exp_db.open()

    eventbus.init(RedisConfig(rds))

    # experiment services (request generators)
    services = [
        ExperimentService(
            'squeezenet',
            # TODO: parameterize path
            ImageClassificationRequestFactory('squeezenet', 'resources/images/small')
        ),
        ExperimentService(
            'alexnet',
            # TODO: parameterize path
            ImageClassificationRequestFactory('alexnet', 'resources/images/small')
        )
    ]

    # client services
    registry = ServiceRegistry()
    registry.register('squeezenet', MXNetImageClassifierService('squeezenet'))
    registry.register('alexnet', MXNetImageClassifierService('alexnet'))
    # balancer = StaticLocalhostBalancer()  # TODO parameterize
    balancer = RedisConnectedBalancer(rds)
    router = Router(registry, balancer)

    # run host
    host = ExperimentHost(rds, services, router=router, trace_logging=args.trace_logging, experiment_db=exp_db)

    log.info('using balancer: %s', balancer)
    try:
        log.info('starting experiment host %s', host.host_name)
        host.run()
    except KeyboardInterrupt:
        pass
    finally:
        host.close()

    print('done, bye')


if __name__ == '__main__':
    main()

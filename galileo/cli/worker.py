import argparse
import logging

import redis
import symmetry.eventbus as eventbus
from symmetry.eventbus.redis import RedisConfig
from symmetry.gateway import SymmetryServiceRouter, SymmetryHostRouter, WeightedRandomBalancer, StaticRouter
from symmetry.service.routing import ReadOnlyListeningRedisRoutingTable

from galileo.experiment.db.factory import create_experiment_database
from galileo.worker import ExperimentWorker
from galileo.worker.client import ClientEmulator, ImageClassificationRequestFactory

log = logging.getLogger(__name__)


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
        exp_db = create_experiment_database('mysql')
        exp_db.open()

    eventbus.init(RedisConfig(rds))

    # experiment services (request generators)
    services = [
        ClientEmulator(
            'squeezenet', ImageClassificationRequestFactory('squeezenet', 'resources/images/small')
        ),
        ClientEmulator(
            'alexnet', ImageClassificationRequestFactory('alexnet', 'resources/images/small')
        )
    ]

    # Router
    rtable = ReadOnlyListeningRedisRoutingTable(rds)
    balancer = WeightedRandomBalancer(rtable)
    router = SymmetryServiceRouter(balancer)
    # router = StaticRouter('http://localhost:8080')
    # router = SymmetryHostRouter(balancer)

    # run host
    host = ExperimentWorker(rds, services, router=router, trace_logging=args.trace_logging, experiment_db=exp_db)

    try:
        rtable.start()
        log.info('starting experiment host %s', host.host_name)
        host.run()
    except KeyboardInterrupt:
        pass
    finally:
        rtable.stop(2)
        host.close()

    print('done, bye')


if __name__ == '__main__':
    main()

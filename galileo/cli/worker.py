import argparse
import logging
import os
import pymq
from pymq.provider.redis import RedisConfig

from galileo.worker import ExperimentWorker
from galileo.worker.client import ClientEmulator, ImageClassificationRequestFactory
from galileo.worker.context import Context

log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--logging', required=False,
                        help='set log level (DEBUG|INFO|WARN|...) to activate logging',
                        default=os.getenv('galileo_logging_level'))
    args = parser.parse_args()

    if args.logging:
        logging.basicConfig(level=logging._nameToLevel[args.logging])

    context = Context()

    redis = require_redis(context)
    pymq.init(RedisConfig(redis))

    # experiment services (request generators)
    services = [
        ClientEmulator(
            'squeezenet', ImageClassificationRequestFactory('squeezenet', 'resources/images/small')
        ),
        ClientEmulator(
            'alexnet', ImageClassificationRequestFactory('alexnet', 'resources/images/small')
        )
    ]

    # run host
    host = ExperimentWorker(context, services)

    try:
        log.info('starting experiment host %s', host.host_name)
        host.run()
    except KeyboardInterrupt:
        pass
    finally:
        host.close()

    print('done, bye')


def require_redis(context):
    try:
        redis = context.create_redis()
        redis.randomkey()  # guard for redis connection
        return redis
    except Exception as e:
        print('Could not initiate Redis connection:', e)
        exit(1)
        raise e


if __name__ == '__main__':
    main()

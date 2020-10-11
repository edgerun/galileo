import argparse
import logging
import os
import signal

import pymq
from pymq.provider.redis import RedisConfig

from galileo.worker.context import Context
from galileo.worker.daemon import WorkerDaemon

logger = logging.getLogger(__name__)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser()
    parser.add_argument('--logging', required=False,
                        help='set log level (DEBUG|INFO|WARN|...) to activate logging',
                        default=os.getenv('galileo_logging_level'))
    args = parser.parse_args()

    if args.logging:
        logging.basicConfig(level=logging._nameToLevel[args.logging])

    context = Context()

    redis = require_redis(context)
    eventbus = pymq.init(RedisConfig(redis))

    # run worker
    worker = WorkerDaemon(context, eventbus=eventbus)

    try:
        logger.info('starting experiment worker %s', worker.name)
        worker.run()
    except KeyboardInterrupt:
        pass
    finally:
        worker.close()

    logger.info('done, bye')


def require_redis(context):
    try:
        redis = context.create_redis()
        redis.randomkey()  # guard for redis connection
        return redis
    except Exception as e:
        print('Could not initiate Redis connection:', e)

    exit(1)


def signal_handler(signum, frame):
    raise KeyboardInterrupt


if __name__ == '__main__':
    main()

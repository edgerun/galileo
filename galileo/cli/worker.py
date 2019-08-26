import argparse
import logging

import pymq

from galileo.worker import ExperimentWorker
from galileo.worker.client import ClientEmulator, ImageClassificationRequestFactory
from galileo.worker.context import Context

log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--logging', required=False,
                        help='set log level (DEBUG|INFO|WARN|...) to activate logging')

    args = parser.parse_args()

    if args.logging:
        logging.basicConfig(level=logging._nameToLevel[args.logging])

    context = Context()

    redis = context.create_redis()
    pymq.init(redis)

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


if __name__ == '__main__':
    main()

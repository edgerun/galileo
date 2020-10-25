import argparse
import logging
import os
import signal

import pymq
import redis
from galileodb.factory import create_experiment_database_from_env
from galileodb.recorder import ExperimentTelemetryRecorder
from pymq.provider.redis import RedisConfig

from galileo.controller import ExperimentController
from galileo.experiment.experimentd import ExperimentDaemon
from galileo.experiment.service import SimpleExperimentService

logger = logging.getLogger(__name__)


def main():
    signal.signal(signal.SIGTERM, handle_sigterm)
    parser = argparse.ArgumentParser()
    parser.add_argument('--logging', required=False,
                        help='set log level (DEBUG|INFO|WARN|...) to activate logging',
                        default=os.getenv('galileo_logging_level'))
    args = parser.parse_args()

    if args.logging:
        logging.basicConfig(level=logging._nameToLevel[args.logging])

    rds = redis.Redis(
        host=os.getenv('galileo_redis_host', 'localhost'),
        port=int(os.getenv('galileo_redis_port', 6379)),
        decode_responses=True
    )
    pymq.init(RedisConfig(rds))

    exp_db = create_experiment_database_from_env()
    exp_db.open()

    def recorder_factory(exp_id: str):
        return ExperimentTelemetryRecorder(rds, exp_db, exp_id)

    try:
        exp_controller = ExperimentController(rds)
        exp_service = SimpleExperimentService(exp_db)

        daemon = ExperimentDaemon(rds, recorder_factory, exp_controller, exp_service)
        daemon.run()
    finally:
        exp_db.close()


def handle_sigterm(*args):
    raise KeyboardInterrupt()


if __name__ == '__main__':
    main()

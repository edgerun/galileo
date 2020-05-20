import argparse
import logging
import os
import signal
import time

import pymq
import redis
from pymq.provider.redis import RedisConfig

from galileo.experiment.db.factory import create_experiment_database_from_env
from galileo.experiment.model import Experiment, generate_experiment_id
from galileo.experiment.service.experiment import SimpleExperimentService
from galileo.experiment.service.telemetry import ExperimentTelemetryRecorder

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGTERM, handle_sigterm)
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=False,
                        help='set name of experiment',
                        default='')
    parser.add_argument('--creator', required=False,
                        help='set name of creator',
                        default='')
    args = parser.parse_args()
    id = generate_experiment_id()
    if args.name:
        name = args.name
    else:
        name = id

    if args.creator:
        creator = args.creator
    else:
        creator = 'galileo-telemetry-' + str(os.getpid())

    rds = redis.Redis(
        host=os.getenv('galileo_redis_host', 'localhost'),
        port=int(os.getenv('galileo_redis_port', 6379)),
        decode_responses=True
    )
    pymq.init(RedisConfig(rds))

    exp_db = create_experiment_database_from_env()
    exp_db.open()

    exp_service = SimpleExperimentService(exp_db)
    exp = Experiment(id=id, name=name, creator=creator, start=time.time(), created=time.time(), status='RUNNING')
    exp_service.save(exp)

    recorder = None
    try:
        logger.info('Start TelemetryRecorder')
        recorder = ExperimentTelemetryRecorder(rds, exp_db, id)
        recorder.run()
    except KeyboardInterrupt:
        pass
    finally:
        exp_service.finalize_experiment(exp, 'FINISHED')
        logger.info('Closing TelemetryRecorder')
        if recorder:
            recorder.close()
        exp_db.close()


def handle_sigterm(*args):
    raise KeyboardInterrupt()


if __name__ == '__main__':
    main()

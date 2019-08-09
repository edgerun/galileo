import argparse
import logging
import os

import redis
import symmetry.eventbus as eventbus
from symmetry.eventbus.redis import RedisConfig

from galileo.controller import ExperimentController
from galileo.experiment.db.factory import create_experiment_database_from_env
from galileo.experiment.experimentd import ExperimentDaemon
from galileo.experiment.service.experiment import SimpleExperimentService
from galileo.experiment.service.instructions import SimpleInstructionService
from galileo.experiment.service.telemetry import ExperimentTelemetryRecorder

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--logging', required=False,
                        help='set log level (DEBUG|INFO|WARN|...) to activate logging')
    args = parser.parse_args()

    if args.logging:
        logging.basicConfig(level=logging._nameToLevel[args.logging])

    rds = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), decode_responses=True)

    eventbus.init(RedisConfig(rds))

    exp_db = create_experiment_database_from_env()
    exp_db.open()

    def recorder_factory(exp_id: str):
        return ExperimentTelemetryRecorder(rds, exp_db, exp_id)

    try:
        exp_controller = ExperimentController(rds)
        ins_service = SimpleInstructionService(exp_db)
        exp_service = SimpleExperimentService(exp_db)

        daemon = ExperimentDaemon(rds, recorder_factory, exp_controller, exp_service, ins_service)
        daemon.run()
    finally:
        exp_db.close()


if __name__ == '__main__':
    main()

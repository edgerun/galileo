import argparse
import logging
import os

import redis
import symmetry.eventbus as eventbus
from symmetry.eventbus.redis import RedisConfig

from galileo.controller import ExperimentController
from galileo.experiment.db import ExperimentDatabase
from galileo.experiment.db.sql import ExperimentSQLDatabase
from galileo.experiment.experimentd import ExperimentDaemon
from galileo.experiment.service.experiment import SimpleExperimentService
from galileo.experiment.service.instructions import SimpleInstructionService
from galileo.experiment.service.telemetry import ExperimentTelemetryRecorder

logger = logging.getLogger(__name__)


def init_database() -> ExperimentDatabase:
    db_type = os.getenv('DB_TYPE', 'sqlite')

    if db_type == 'sqlite':
        from galileo.experiment.db.sql.sqlite import SqliteAdapter
        db_file = os.getenv('SQLITE_PATH', '/tmp/galileo.sqlite')
        logger.info('creating db adapter to SQLite %s', db_file)
        db_adapter = SqliteAdapter(db_file)

    elif db_type == 'mysql':
        from galileo.experiment.db.sql.mysql import MysqlAdapter
        logger.info('creating db adapter for MySQL from environment variables')
        db_adapter = MysqlAdapter.create_from_env()

    else:
        raise ValueError('unknown database type %s' % db_type)

    return ExperimentSQLDatabase(db_adapter)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--logging', required=False,
                        help='set log level (DEBUG|INFO|WARN|...) to activate logging')
    args = parser.parse_args()

    if args.logging:
        logging.basicConfig(level=logging._nameToLevel[args.logging])

    rds = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), decode_responses=True)

    eventbus.init(RedisConfig(rds))

    exp_db = init_database()
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

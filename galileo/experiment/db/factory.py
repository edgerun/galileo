import os
import logging

from galileo.experiment.db import ExperimentDatabase
from galileo.experiment.db.sql import ExperimentSQLDatabase

logger = logging.getLogger(__name__)


def create_experiment_database_from_env() -> ExperimentDatabase:
    db_type = os.getenv('DB_TYPE', 'sqlite')
    return create_experiment_database(db_type)


def create_experiment_database(db_type: str) -> ExperimentDatabase:
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

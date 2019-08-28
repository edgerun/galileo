import logging
import os
from typing import MutableMapping

from galileo.experiment.db import ExperimentDatabase
from galileo.experiment.db.sql import ExperimentSQLDatabase
from galileo.experiment.db.sql.mysql import MysqlAdapter

logger = logging.getLogger(__name__)


def create_experiment_database_from_env(env: MutableMapping = os.environ) -> ExperimentDatabase:
    driver = env.get('galileo_expdb_driver', 'sqlite')
    return create_experiment_database(driver)


def create_experiment_database(driver: str, env: MutableMapping = os.environ) -> ExperimentDatabase:
    if driver == 'sqlite':
        from galileo.experiment.db.sql.sqlite import SqliteAdapter
        db_file = env.get('galileo_expdb_sqlite_path', '/tmp/galileo.sqlite')
        logger.info('creating db adapter to SQLite %s', db_file)
        db_adapter = SqliteAdapter(db_file)

    elif driver == 'mysql':
        from galileo.experiment.db.sql.mysql import MysqlAdapter
        logger.info('creating db adapter for MySQL from environment variables')
        db_adapter = create_mysql_from_env(env)

    else:
        raise ValueError('unknown database driver %s' % driver)

    return ExperimentSQLDatabase(db_adapter)


def create_mysql_from_env(env: MutableMapping = os.environ):
    params = {
        'host': env.get('galileo_expdb_mysql_host', 'localhost'),
        'port': int(env.get('galileo_expdb_mysql_port', '3307')),
        'user': env.get('galileo_expdb_mysql_user', None),
        'password': env.get('galileo_expdb_mysql_password', None),
        'db': env.get('galileo_expdb_mysql_db', None)
    }

    logger.info('read mysql adapter parameters from environment %s', params)
    return MysqlAdapter(**params)

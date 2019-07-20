import logging

import mysql.connector as mysql

from galileo.experiment.db.sql import SqlAdapter

logger = logging.getLogger(__name__)


class MysqlAdapter(SqlAdapter):
    placeholder = '%s'

    def _connect(self, *args, **kwargs):
        logger.info('connecting to mysql db with args %s', kwargs)
        return mysql.connect(**kwargs)

    def cursor(self):
        try:
            return self.db.cursor()
        except:
            logger.warning('tyring to reconnect...')
            self.reconnect()
            return self.db.cursor()

    def executescript(self, *args, **kwargs):
        script = args[0]
        # FIXME: pretty hacky
        schema = ' '.join(script.splitlines())
        statements = [stmt.strip() for stmt in schema.split(';')]

        cur = self.db.cursor()
        try:
            for stmt in statements:
                if stmt:
                    cur.execute(stmt)
            self.db.commit()
        except:
            self.db.rollback()

    @staticmethod
    def create_from_env():
        import os

        params = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', '3307')),
            'user': os.getenv('MYSQL_USER', None),
            'password': os.getenv('MYSQL_PASSWORD', None),
            'db': os.getenv('MYSQL_DB', None)
        }
        logger.info('read mysql adapter parameters from environment %s', params)
        return MysqlAdapter(**params)

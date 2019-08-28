import logging

import mysql.connector as mysql

from galileo.experiment.db.sql import SqlAdapter

logger = logging.getLogger(__name__)


class MysqlAdapter(SqlAdapter):
    placeholder = '%s'

    def _connect(self, *args, **kwargs):
        logger.info('connecting to mysql db with args %s', kwargs)
        con = mysql.connect(**kwargs)
        con.autocommit = True
        return con

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

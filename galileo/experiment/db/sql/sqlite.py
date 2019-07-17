import sqlite3

from galileo.experiment.db.sql import SqlAdapter


class SqliteAdapter(SqlAdapter):
    placeholder = '?'

    def _connect(self, *args, **kwargs):
        return sqlite3.connect(*args, **kwargs)

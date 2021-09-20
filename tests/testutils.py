import os
import shutil
import tempfile

import redislite
from galileodb.sql.adapter import ExperimentSQLDatabase, SqlAdapter
from galileodb.sql.driver.sqlite import SqliteAdapter

from galileo.util import poll


class TestResource(object):

    def setUp(self):
        pass

    def tearDown(self):
        pass


class RedisResource(TestResource):
    tmpfile: str
    rds: redislite.Redis

    def setUp(self):
        self.tmpfile = tempfile.mktemp('.db', 'galileo_test_')
        self.rds = redislite.Redis(self.tmpfile, decode_responses=True)
        self.rds.get('dummykey')  # run a first command to initiate

    def tearDown(self):
        self.rds.shutdown()

        os.remove(self.tmpfile)
        os.remove(self.rds.redis_configuration_filename)
        os.remove(self.rds.settingregistryfile)
        shutil.rmtree(self.rds.redis_dir)

        self.rds = None
        self.tmpfile = None


class SqliteResource(TestResource):
    db_file = None

    sql: SqlAdapter
    db: ExperimentSQLDatabase

    def setUp(self) -> None:
        self.db_file = tempfile.mktemp('.sqlite', 'galileo_test_')
        self.sql = SqliteAdapter(self.db_file)
        self.db = ExperimentSQLDatabase(self.sql)
        self.db.open()

    def tearDown(self) -> None:
        self.db.close()
        os.remove(self.db_file)


def assert_poll(condition, msg='Condition failed', timeout=2):
    try:
        poll(condition, timeout, 0.01)
    except TimeoutError:
        raise AssertionError(msg)

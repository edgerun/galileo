import unittest

from galileo.experiment.db.sql.mysql import MysqlAdapter
from tests.test_experiment_db import AbstractTestSqlDatabase


class TestMariaDatabase(AbstractTestSqlDatabase, unittest.TestCase):

    def tearDown(self) -> None:
        self.sql.execute('DROP TABLE IF EXISTS `instructions`')
        self.sql.execute('DROP TABLE IF EXISTS `experiments`')
        self.sql.execute('DROP TABLE IF EXISTS `traces`')
        self.sql.execute('DROP TABLE IF EXISTS `telemetry`')

    def _create_sql_adapter(self):
        return MysqlAdapter(host='127.0.0.1', port=3307, user='galileo', password='galileo', db='galileo')


if __name__ == '__main__':
    unittest.main()

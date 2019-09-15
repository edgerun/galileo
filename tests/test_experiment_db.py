import abc

from galileo.experiment.db.sql import ExperimentSQLDatabase, SqlAdapter
from galileo.experiment.model import Experiment, Telemetry


class AbstractTestSqlDatabase(abc.ABC):
    sql: SqlAdapter
    db: ExperimentSQLDatabase

    def setUp(self) -> None:
        self.sql = self._create_sql_adapter()
        self.db = ExperimentSQLDatabase(self.sql)
        self.db.open()

    def tearDown(self) -> None:
        self.db.close()

    def _create_sql_adapter(self) -> SqlAdapter:
        raise NotImplementedError

    def test_get_experiment_on_invalid_id(self):
        result = self.db.get_experiment('NOTEXISTS')
        self.assertIsNone(result)

    def test_save_and_get_experiment(self):
        expected = Experiment('expid1', 'test_experiment', 'unittest', 10, 100, 1, 'running')

        self.db.save_experiment(expected)

        actual = self.db.get_experiment('expid1')

        self.assertEqual('expid1', actual.id)
        self.assertEqual('test_experiment', actual.name)
        self.assertEqual('unittest', actual.creator)
        self.assertEqual(10., actual.start)
        self.assertEqual(100., actual.end)
        self.assertEqual(1., actual.created)
        self.assertEqual('running', actual.status)

    def test_insert_many_and_count(self):
        entries = [
            ('expid3', 'test_experiment', 'unittest2', 'running'),
            ('expid4', 'test_experiment', 'unittest2', 'running'),
            ('expid5', 'test_experiment', 'unittest2', 'running')
        ]

        self.sql.insert_many('experiments', ['exp_id', 'name', 'creator', 'status'], entries)

        cur = self.sql.cursor()
        cur.execute('SELECT COUNT(*) FROM experiments WHERE `CREATOR` = "unittest2"')
        val = cur.fetchone()
        self.assertEqual(3, val[0])

    def test_update_and_get(self):
        self.db.save_experiment(Experiment('expid6', 'test_experiment', 'unittest', 10, 100, 1, 'finished'))
        self.db.save_experiment(Experiment('expid7', 'test_experiment', 'unittest', 100, None, 10, 'running'))

        self.sql.update_by_id('experiments', ('exp_id', 'expid7'), {'status': 'finished', 'end': 1000})

        exp2 = self.db.get_experiment('expid7')

        self.assertEqual('expid7', exp2.id)
        self.assertEqual('test_experiment', exp2.name)
        self.assertEqual('unittest', exp2.creator)
        self.assertEqual(100., exp2.start)
        self.assertEqual(1000., exp2.end)
        self.assertEqual(10., exp2.created)
        self.assertEqual('finished', exp2.status)

    def test_update_experiment_and_get(self):
        exp = Experiment('expid8', 'test_experiment', 'unittest', 10, None, 1, 'running')
        self.db.save_experiment(exp)

        self.assertEqual(self.db.get_experiment('expid8').status, 'running')
        self.assertEqual(self.db.get_experiment('expid8').end, None)

        exp.status = 'finished'
        exp.end = 100

        self.db.update_experiment(exp)

        self.assertEqual(self.db.get_experiment('expid8').status, 'finished')
        self.assertEqual(self.db.get_experiment('expid8').end, 100)

    def test_save_telemetry(self):
        telemetry = [
            Telemetry(1, 'cpu', 'n1', 32, 'expid1'),
            Telemetry(2, 'cpu', 'n1', 33, 'expid1'),
            Telemetry(3, 'cpu', 'n1', 31, 'expid1'),
        ]

        self.db.save_telemetry(telemetry)

        rows = self.db.db.fetchall('SELECT * FROM telemetry')
        self.assertEqual(3, len(rows))

    def test_delete_experiment(self):
        exp_id = 'expid10'
        exp_id_control = 'expid11'
        self.db.save_experiment(Experiment(exp_id, 'test_experiment', 'unittest', 10, 100, 1, 'finished'))
        self.db.save_telemetry([Telemetry(1, 'cpu', 'n1', 32, exp_id)])

        self.db.save_experiment(Experiment(exp_id_control, 'test_experiment', 'unittest', 10, 100, 1, 'finished'))
        self.db.save_telemetry([Telemetry(1, 'cpu', 'n1', 32, exp_id_control)])

        self.assertIsNotNone(self.db.get_experiment(exp_id))
        telemetry_rows = self.db.db.fetchall('SELECT * FROM telemetry WHERE EXP_ID = "%s"' % exp_id)
        self.assertEqual(1, len(telemetry_rows))

        self.db.delete_experiment(exp_id)

        self.assertIsNone(self.db.get_experiment(exp_id))
        telemetry_rows = self.db.db.fetchall('SELECT * FROM telemetry WHERE EXP_ID = "%s"' % exp_id)
        self.assertEqual(0, len(telemetry_rows))

        self.assertIsNotNone(self.db.get_experiment(exp_id_control))
        telemetry_rows = self.db.db.fetchall('SELECT * FROM telemetry WHERE EXP_ID = "%s"' % exp_id_control)
        self.assertEqual(1, len(telemetry_rows))

import abc
import logging
import threading
from typing import Tuple, List, Dict

from galileo.experiment.db import ExperimentDatabase
from galileo.experiment.model import Experiment, Telemetry, ServiceRequestTrace, NodeInfo

logger = logging.getLogger(__name__)


class SqlAdapter(abc.ABC):
    placeholder = '?'

    _thread_local = threading.local()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self._thread_local.connection = None
        self.connect_args = args
        self.connect_kwargs = kwargs

    @property
    def connection(self):
        if 'connection' not in self._thread_local.__dict__ or self._thread_local.connection is None:
            logger.info('%s connecting to database', threading.current_thread().name)
            self._thread_local.connection = self._connect(*self.connect_args, **self.connect_kwargs)
        return self._thread_local.connection

    def reconnect(self):
        self.close()
        self.open()

    @property
    def db(self):
        return self.connection

    def cursor(self):
        return self.db.cursor()

    def execute(self, *args, **kwargs):
        cur = self.cursor()
        try:
            logger.debug('executing SQL %s %s', args, kwargs)
            cur.execute(*args, **kwargs)
            self.db.commit()
        finally:
            cur.close()

    def executemany(self, *args, **kwargs):
        cur = self.cursor()
        try:
            cur.executemany(*args, **kwargs)
            self.db.commit()
        finally:
            cur.close()

    def executescript(self, *args, **kwargs):
        cur = self.cursor()
        try:
            cur.executescript(*args, **kwargs)
            self.db.commit()
        finally:
            cur.close()

    def fetchone(self, *args, **kwargs):
        cur = self.cursor()
        try:
            cur.execute(*args, **kwargs)
            return cur.fetchone()
        finally:
            cur.close()

    def fetchmany(self, *args, **kwargs):
        cur = self.cursor()
        try:
            cur.execute(*args, **kwargs)
            return cur.fetchmany()
        finally:
            cur.close()

    def fetchall(self, *args, **kwargs):
        cur = self.cursor()
        try:
            cur.execute(*args, **kwargs)
            return cur.fetchall()
        finally:
            cur.close()

    def open(self):
        assert self.connection is not None

    def close(self):
        if 'connection' in self._thread_local.__dict__ and self._thread_local.connection is not None:
            try:
                self._thread_local.connection.close()
            finally:
                self._thread_local.connection = None

    def insert_one(self, table: str, data: Dict[str, object]):
        columns, values = list(), list()

        for key, value in data.items():
            columns.append('`%s`' % key.upper())
            values.append(value)

        columns = ','.join(columns)
        placeholders = ','.join([self.placeholder] * len(values))

        # TODO: sanitize table and column inputs
        sql = 'INSERT INTO `%s` (%s) VALUES (%s)' % (table, columns, placeholders)

        logger.debug('running insert sql: %s' % sql)

        self.execute(sql, values)

    def insert_many(self, table: str, keys, data: List):
        columns = ','.join(['`%s`' % key.upper() for key in keys])
        placeholders = ','.join([self.placeholder] * len(keys))

        # TODO: sanitize table and column inputs
        sql = 'INSERT INTO `%s` (%s) VALUES (%s)' % (table, columns, placeholders)

        logger.debug('running insert many sql: %s', sql)

        self.executemany(sql, data)

    def update_by_id(self, table: str, identity: Tuple[str, object], data: Dict[str, object]):
        set_statements, values = list(), list()
        id_col, id_val = identity

        for key, value in data.items():
            set_statements.append('`%s` = %s' % (key.upper(), self.placeholder))
            values.append(value)

        values.append(id_val)

        # TODO: sanitize table and column inputs
        sql = 'UPDATE `{table}` SET {set_statements} WHERE `{id_col}` = ' + self.placeholder
        sql = sql.format(table=table, set_statements=','.join(set_statements), id_col=id_col)

        logger.debug('running update sql: %s', sql)
        self.execute(sql, values)

    def _connect(self, *args, **kwargs):
        raise NotImplementedError


class ExperimentSQLDatabase(ExperimentDatabase):
    SCHEMA = '''

    CREATE TABLE IF NOT EXISTS experiments
    (
        EXP_ID  VARCHAR(255) NOT NULL,
        NAME    VARCHAR(255),
        CREATOR VARCHAR(255),
        START   DOUBLE,
        END     DOUBLE,
        CREATED DOUBLE,
        STATUS  VARCHAR(255) NOT NULL,
        CONSTRAINT experiments_pk PRIMARY KEY (EXP_ID)
    );

    CREATE TABLE IF NOT EXISTS nodeinfo
    (
        EXP_ID      VARCHAR(255) NOT NULL,
        NODE        VARCHAR(255) NOT NULL,
        INFO_KEY    VARCHAR(255),
        INFO_VALUE  VARCHAR(255)
    );

    CREATE TABLE IF NOT EXISTS traces
    (
        EXP_ID  VARCHAR(255),
        CLIENT  VARCHAR(255) NOT NULL,
        SERVICE VARCHAR(255) NOT NULL,
        HOST    VARCHAR(255),
        CREATED DOUBLE,
        SENT    DOUBLE,
        DONE    DOUBLE
    );

    CREATE TABLE IF NOT EXISTS telemetry
    (
        EXP_ID    VARCHAR(255) NOT NULL,
        TIMESTAMP DOUBLE       NOT NULL,
        METRIC    varchar(255) NOT NULL,
        NODE      varchar(255) NOT NULL,
        VALUE     DOUBLE       NOT NULL
    );
    '''

    def __init__(self, db: SqlAdapter) -> None:
        super().__init__()
        self.db = db

    def open(self):
        self.db.open()
        self.db.executescript(self.SCHEMA)

    def close(self):
        self.db.close()

    def save_experiment(self, experiment: Experiment):
        data = dict(experiment.__dict__)
        data['exp_id'] = data['id']
        del data['id']
        logger.debug('saving experiment with data %s', data)
        self.db.insert_one('experiments', data)

    def update_experiment(self, experiment: Experiment):
        data = dict(experiment.__dict__)
        del data['id']

        self.db.update_by_id('experiments', ('exp_id', experiment.id), data)

    def delete_experiment(self, exp_id: str):
        experiment = self.get_experiment(exp_id)
        if experiment is None:
            raise ValueError('No such experiment %s' % exp_id)

        stmts = [
            "DELETE FROM `telemetry` WHERE EXP_ID = " + self.db.placeholder,
            "DELETE FROM `traces` WHERE EXP_ID = " + self.db.placeholder,
            "DELETE FROM `experiments` WHERE EXP_ID = " + self.db.placeholder,
        ]

        for sql in stmts:
            try:
                self.db.execute(sql, (exp_id,))
            except Exception as e:
                logger.exception('Exception while executing %s', sql, e)

    def get_experiment(self, exp_id: str) -> Experiment:
        sql = "SELECT * FROM `experiments` WHERE EXP_ID = " + self.db.placeholder

        entry = self.db.fetchone(sql, (exp_id,))

        if entry:
            row = tuple(entry)
            return Experiment(*row)
        else:
            return None

    def save_traces(self, traces: List[ServiceRequestTrace]):
        self.db.insert_many('traces', ServiceRequestTrace._fields, traces)

    def touch_traces(self, experiment: Experiment):
        sql = 'UPDATE `traces` SET `EXP_ID` = ? WHERE CREATED >= ? AND CREATED <= ?'
        sql = sql.replace('?', self.db.placeholder)
        self.db.execute(sql, (experiment.id, experiment.start, experiment.end))

    def save_telemetry(self, telemetry: List[Telemetry]):
        self.db.insert_many('telemetry', Telemetry._fields, telemetry)

    def save_nodeinfos(self, infos: List[NodeInfo]):
        keys = ['exp_id', 'node', 'info_key', 'info_value']

        data = list()
        for info in infos:
            for k, v in info.data.items():
                data.append((info.exp_id, info.node, k, v))

        self.db.insert_many('nodeinfo', keys, data)

    def find_all(self) -> List[Experiment]:
        sql = 'SELECT * FROM `experiments`'

        entries = self.db.fetchall(sql)

        return list(map(lambda x: Experiment(*(tuple(x))), entries))

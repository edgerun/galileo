import csv
import logging
import os
from multiprocessing import Process
from multiprocessing.queues import Queue
from queue import Empty
from typing import List, Iterable

import redis

from galileo import util
from galileo.experiment.db import ExperimentDatabase
from galileo.experiment.db.sql import ExperimentSQLDatabase
from galileo.experiment.model import ServiceRequestTrace

logger = logging.getLogger(__name__)

POISON = "__POISON__"
START = "__START__"
PAUSE = "__PAUSE__"
FLUSH = '__FLUSH__'


class TraceLogger(Process):
    flush_interval = 20

    def __init__(self, trace_queue: Queue, start=True) -> None:
        super().__init__()
        self.traces = trace_queue
        self.closed = False
        self.buffer = list()
        self.running = start

    def run(self):
        try:
            return self._loop()
        finally:
            self.flush()

    def flush(self):
        if not self.buffer:
            logger.debug('Buffer empty, not flushing')
            return

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Flushing trace buffer')

        self._do_flush(self.buffer)

        self.buffer.clear()

    def close(self):
        self.closed = True
        self.traces.put(POISON)

    def _loop(self):
        timeout = None
        while True:
            if self.closed and timeout is None:
                logger.debug('setting read timeout to 2 seconds')
                timeout = 2

            try:
                trace = self.traces.get(timeout=timeout)

                if trace == POISON:
                    logger.debug('poison received, setting closed to true')
                    self.closed = True
                    break
                elif trace == FLUSH:
                    logger.debug('flush command received, flushing buffer')
                    self.flush()
                    continue
                elif trace == START:
                    logger.debug('start received')
                    self.running = True
                    continue
                elif trace == PAUSE:
                    logger.debug('pause received, flushing remaining traces')
                    self.running = False
                    self.flush()
                    continue

                if self.running:
                    self.buffer.append(trace)

                if len(self.buffer) >= self.flush_interval:
                    logger.debug('flush interval reached, flushing buffer')
                    self.flush()

            except KeyboardInterrupt:
                break
            except Empty:
                logger.debug('queue is empty, exitting')
                return

    def _do_flush(self, buffer: List[ServiceRequestTrace]):
        pass


class TraceRedisLogger(TraceLogger):
    key = 'galileo:results:traces'

    def __init__(self, trace_queue: Queue, rds: redis.Redis, start=True) -> None:
        super().__init__(trace_queue, start)
        self.rds = rds

    def _do_flush(self, buffer: Iterable[ServiceRequestTrace]):
        rds = self.rds.pipeline()

        for trace in buffer:
            score = trace.created
            value = '%s,%s,%s,%.7f,%.7f,%.7f' % trace  # FIXME
            rds.zadd(self.key, {value: score})

        rds.execute()


class TraceDatabaseLogger(TraceLogger):

    def __init__(self, trace_queue: Queue, experiment_db: ExperimentDatabase, start=True) -> None:
        super().__init__(trace_queue, start)
        self.experiment_db = experiment_db

    def run(self):
        if isinstance(self.experiment_db, ExperimentSQLDatabase):
            # this is a terrible hack due to multiprocessing issues:
            # close() will delete the threadlocal (which is not actually accessible from the process) and create a new
            # connection. The SqlAdapter adapter design may be broken. or python multiprocessing...
            self.experiment_db.db.reconnect()
        super().run()

    def _do_flush(self, buffer: Iterable[ServiceRequestTrace]):
        self.experiment_db.save_traces(list(buffer))


class TraceFileLogger(TraceLogger):

    def __init__(self, trace_queue: Queue, host_name, target_dir='/tmp/mc2/exp', start=True) -> None:
        super().__init__(trace_queue, start)
        self.target_dir = target_dir
        self.file_name = 'traces-%s.csv' % host_name
        self.file_path = os.path.join(self.target_dir, self.file_name)
        util.mkdirp(self.target_dir)

        self.init_file()

    def init_file(self):
        logger.debug('Initializing trace file logger to log into %s', self.file_path)
        if os.path.exists(self.file_path):
            return

        logger.debug('Initializing %s with header', self.file_path)
        with open(self.file_path, 'w') as fd:
            csv.writer(fd).writerow(ServiceRequestTrace._fields)

    def _do_flush(self, buffer: Iterable[ServiceRequestTrace]):
        with open(self.file_path, 'a') as fd:
            writer = csv.writer(fd)
            for row in buffer:
                writer.writerow(row)

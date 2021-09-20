import json
import logging
import os
import time
from contextlib import contextmanager
from json import JSONDecodeError
from typing import Callable

import pymq
import redis
from galileodb.model import Experiment, QueuedExperiment, ExperimentConfiguration, generate_experiment_id
from telemc import TelemetryRecorder

from galileo.controller import ExperimentController, RedisClusterController
from galileo.experiment import runner
from galileo.experiment.service import ExperimentService
from galileo.worker.api import StartTracingCommand, PauseTracingCommand

logger = logging.getLogger(__name__)


class ExperimentDaemon:
    POISON = '__POISON__'

    def __init__(self, rds: redis.Redis, create_recorder: Callable[[str], TelemetryRecorder],
                 exp_controller: ExperimentController, exp_service: ExperimentService) -> None:
        self.rds = rds
        self.create_recorder = create_recorder
        self.exp_controller = exp_controller
        self.exp_service = exp_service
        self.closed = False

        self.queue = None

    def close(self):
        self.closed = True
        if self.queue:
            self.queue.put_nowait(self.POISON)

    def run(self) -> None:
        self.queue = pymq.queue(ExperimentController.queue_key)

        try:
            logger.info('listening for incoming experiment...')
            while not self.closed:
                item = self.queue.get()

                if item == self.POISON:
                    break

                exp = None
                try:
                    logger.debug('got queued experiment %s', item)
                    exp, cfg = self.load_experiment(item)
                except Exception as e:
                    if exp and exp.id:
                        exp = self.exp_service.find(exp.id)
                        if exp is not None:
                            exp.status = 'FAILED'
                            self.exp_service.save(exp)

                    logger.exception('error while loading experiment from queue')
                    continue

                status = exp.status
                try:
                    pymq.publish(StartTracingCommand())
                    self.run_experiment(exp, cfg)
                    status = 'FINISHED'
                except Exception as e:
                    logger.error('error while running experiment: %s', e)
                    status = 'FAILED'
                finally:
                    pymq.publish(PauseTracingCommand())
                    logger.info("finalizing experiment %s", exp.id)
                    self.exp_service.finalize_experiment(exp, status)

        except KeyboardInterrupt:
            logger.info("interrupted while listening")

        logger.info('exiting experiment daemon loop')

    def run_experiment(self, exp: Experiment, cfg: ExperimentConfiguration):
        exp.status = 'IN_PROGRESS'
        exp.start = time.time()
        self.exp_service.save(exp)

        with managed_recorder(self.create_recorder, exp.id):
            logger.info("starting experiment %s", exp.id)
            runner.run_experiment(RedisClusterController(self.rds), cfg)

    def load_experiment(self, queued: QueuedExperiment) -> (Experiment, ExperimentConfiguration):
        exp = self.exp_service.find(queued.experiment.id) if queued.experiment.id else None

        if not exp:
            exp = queued.experiment

        if not exp.id:
            exp.id = generate_experiment_id()
        if not exp.name:
            exp.name = exp.id
        if not exp.creator:
            exp.creator = 'galileo-' + str(os.getpid())
        if not exp.created:
            exp.created = time.time()

        return exp, queued.configuration

    @staticmethod
    def _get_json_body(message):
        # parse JSON, mandatory attributes: id, name, creator, instructions
        try:
            return json.loads(message[1])
        except JSONDecodeError as e:
            logger.warning("JSON decoding error while parsing message body", e)
            return None


@contextmanager
def managed_recorder(create_recorder: Callable[[str], TelemetryRecorder], exp_id: str):
    r = create_recorder(exp_id)
    try:
        r.start()
        yield r
    finally:
        r.stop()

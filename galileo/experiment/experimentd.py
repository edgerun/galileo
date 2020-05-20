import io
import json
import logging
import os
import time
from contextlib import contextmanager
from json import JSONDecodeError
from typing import Callable, List

import pymq
import redis
from telemc import TelemetryRecorder

from galileo.controller import ExperimentController, ExperimentShell, create_instructions
from galileo.experiment.model import Experiment, QueuedExperiment, ExperimentConfiguration, generate_experiment_id
from galileo.experiment.service.experiment import ExperimentService
from galileo.worker.api import StartTracingCommand, PauseTracingCommand

logger = logging.getLogger(__name__)


class Instructions:
    exp_id: str
    instructions: List[str]

    def __init__(self, exp_id=None, instructions=None):
        self.exp_id = exp_id
        self.instructions = instructions


class ExperimentBatchShell(ExperimentShell):

    def __init__(self, controller: ExperimentController):
        super().__init__(controller, completekey=None, stdin=io.StringIO(), stdout=io.StringIO())

    def istty(self):
        return False

    def run_batch(self, lines):
        if not lines:
            raise ValueError('empty batch')

        try:
            self.cmdqueue.extend(lines)
            if lines[-1].strip() != 'exit':
                self.cmdqueue.append('exit')

            if logger.isEnabledFor(logging.DEBUG):
                self.debug_cmdqueue()

            self.run()
        except Exception as e:
            logger.error('Error while executing experiment: %s', e)

    def precmd(self, line):
        logger.debug('processing command: %s', line)
        return super().precmd(line)

    def debug_cmdqueue(self):
        lines = self.cmdqueue
        logger.debug("executing %d experiment instructions:", len(lines))
        for i in range(len(lines)):
            logger.debug('line %d: %s', i, lines[i])


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
            logger.info('Listening for incoming experiment instructions...')
            while not self.closed:
                item = self.queue.get()

                if item == self.POISON:
                    break

                exp = None
                try:
                    logger.debug('got queued experiment %s', item)
                    exp, ins = self.load_experiment(item)
                except Exception as e:
                    if exp and exp.id:
                        exp = self.exp_service.find(exp.id)
                        if exp is not None:
                            exp.status = 'FAILED'
                            self.exp_service.save(exp)

                    logger.exception('Error while loading experiment from queue')
                    continue

                status = exp.status
                try:
                    pymq.publish(StartTracingCommand())
                    self.run_experiment(exp, ins)
                    status = 'FINISHED'
                except Exception as e:
                    logger.error('Error while running experiment: %s', e)
                    status = 'FAILED'
                finally:
                    pymq.publish(PauseTracingCommand())
                    logger.info("finalizing experiment %s", exp.id)
                    self.exp_service.finalize_experiment(exp, status)

        except KeyboardInterrupt:
            logger.info("Interrupted while listening")

        logger.info('exiting experiment daemon loop')

    def run_experiment(self, exp: Experiment, ins: Instructions):
        exp.status = 'IN_PROGRESS'
        exp.start = time.time()
        self.exp_service.save(exp)

        lines = ins.instructions

        with managed_recorder(self.create_recorder, exp.id):
            logger.info("starting experiment %s", exp.id)

            shell = ExperimentBatchShell(self.exp_controller)
            shell.run_batch(lines)
            # shell.stdout.getvalue() will return whatever the shell would have written to sysout
            # may be useful for logging the result

    def load_experiment(self, queued: QueuedExperiment) -> (Experiment, Instructions):
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

        return exp, self.create_instructions(exp.id, queued.configuration)

    def create_instructions(self, experiment_id, config: ExperimentConfiguration) -> Instructions:
        workers = list(self.exp_controller.list_workers())
        if not workers:
            raise ValueError('no workers to execute the experiment on')

        instructions = create_instructions(config, workers)
        return Instructions(experiment_id, instructions)

    @staticmethod
    def _get_json_body(message):
        # parse JSON, mandatory attributes: id, name, creator, instructions
        try:
            return json.loads(message[1])
        except JSONDecodeError as e:
            logger.warning("JSON Decoding error while parsing message body", e)
            return None


@contextmanager
def managed_recorder(create_recorder: Callable[[str], TelemetryRecorder], exp_id: str):
    r = create_recorder(exp_id)
    try:
        r.start()
        yield r
    finally:
        r.stop()

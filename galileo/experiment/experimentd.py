import io
import json
import logging
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from json import JSONDecodeError
from typing import Callable

import redis
from symmetry.telemetry.recorder import TelemetryRecorder

from galileo.controller import ExperimentController, ControllerShell
from galileo.experiment.model import Experiment, Instructions
from galileo.experiment.service.experiment import ExperimentService
from galileo.experiment.service.instructions import InstructionService
from galileo.util import subdict

logger = logging.getLogger(__name__)


def generate_experiment_id():
    prefix = datetime.strftime(datetime.now(), '%Y%m%d%H%M')
    suffix = str(uuid.uuid4())[:4]
    return prefix + '-' + suffix


class ExperimentBatchShell(ControllerShell):

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
            self.run()
        except Exception as e:
            logger.error('Error while executing experiment: %s', e)

    def precmd(self, line):
        logger.debug('processing command: %s', line)
        return super().precmd(line)


class ExperimentDaemon:

    def __init__(self, rds: redis.Redis, create_recorder: Callable[[str], TelemetryRecorder],
                 exp_controller: ExperimentController, exp_service: ExperimentService,
                 ins_service: InstructionService) -> None:
        self.rds = rds
        self.create_recorder = create_recorder
        self.exp_controller = exp_controller
        self.exp_service = exp_service
        self.ins_service = ins_service
        self.cancelled = False

    def cancel(self):
        self.cancelled = True
        self.rds.lpush(ExperimentController.queue_key, '')

    def run(self) -> None:
        rds = self.rds
        logger.info('Listening for incoming experiment instructions...')
        try:
            while self.cancelled is False:
                message = rds.blpop(ExperimentController.queue_key)
                if not message or not message[1]:
                    print('empty message, skipping')
                    continue

                try:
                    body = self._get_json_body(message)

                    if body is None:
                        logger.warning('Error parsing message to JSON. Message was: %s', message)
                        return

                    logger.debug('experiment payload: %s', body)

                    exp, ins = self.load_experiment(body)
                except Exception as e:
                    # TODO: set experiment status to failed
                    logger.exception('Error while loading experiment from queue')
                    continue

                status = exp.status
                try:
                    self.run_experiment(exp, ins)
                    status = 'FINISHED'
                except Exception as e:
                    logger.error('Error while running experiment: %s', e)
                    status = 'FAILED'
                finally:
                    logger.info("finalizing experiment %s", exp.id)
                    self.exp_service.finalize_experiment(exp, status)

        except KeyboardInterrupt:
            logger.info("Interrupted while listening")

        logger.info('exiting experiment daemon loop')

    def run_experiment(self, exp: Experiment, ins: Instructions):
        exp.status = 'IN_PROGRESS'
        exp.start = time.time()
        self.exp_service.save(exp)
        self.ins_service.save(ins)

        lines = ins.instructions.splitlines()

        with managed_recorder(self.create_recorder, exp.id):
            logger.info("start experiment %s", exp.id)

            shell = ExperimentBatchShell(self.exp_controller)
            shell.run_batch(lines)
            # shell.stdout.getvalue() will return whatever the shell would have written to sysout
            # may be useful for logging the result

    def load_experiment(self, body) -> (Experiment, Instructions):
        exp = self.exp_service.find(body['id']) if 'id' in body else None

        if exp:
            return exp, self.ins_service.find(exp.id)

        exp = Experiment(**subdict(body, ['id', 'name', 'creator', 'status']))

        if not exp.id:
            exp.id = generate_experiment_id()
        if not exp.name:
            exp.name = exp.id
        if not exp.creator:
            exp.creator = 'galileo-' + str(os.getpid())

        ins = Instructions(exp.id, body['instructions'])

        return exp, ins

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

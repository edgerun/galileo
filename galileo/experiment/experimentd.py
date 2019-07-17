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
from galileo.experiment.service.experiment import ExperimentService
from galileo.experiment.service.instructions import InstructionService

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

    def run(self) -> None:
        rds = self.rds
        logger.info('Listening for incoming experiment instructions...')
        try:
            while True:
                message = rds.blpop('exp:experiments:instructions')
                if message:
                    body = self._get_json_body(message)

                    if body is None:
                        logger.warning('Error parsing message to JSON. Message was: %s', message)
                        continue

                    logger.debug('experiment payload: %s', body)
                    if 'id' not in body:
                        body['id'] = generate_experiment_id()

                    if 'name' not in body:
                        body['name'] = body['id']

                    if 'creator' not in body:
                        body['creator'] = 'galileo-' + str(os.getpid())

                    body['status'] = 'IN_PROGRESS'
                    (exp, saved) = self.exp_service.save_json(body)

                    exp.start = time.time()
                    exp.status = 'IN_PROGRESS'
                    self.exp_service.save(exp)

                    if saved:
                        ins = self.ins_service.save_json(exp.id, body)
                        lines = ins.instructions.splitlines()
                    else:
                        lines = self.ins_service.find(exp.id).instructions.splitlines()

                    with managed_recorder(self.create_recorder, exp.id):
                        logger.info("start experiment %s", exp.id)

                        shell = ExperimentBatchShell(self.exp_controller)
                        shell.run_batch(lines)
                        # shell.stdout.getvalue() will return whatever the shell would have written to sysout
                        # may be useful for logging the result

                        logger.info("finalizing experiment %s", exp.id)
                        end = time.time()
                        exp.end = end
                        self.exp_service.finish_experiment(exp)


        except KeyboardInterrupt:
            logger.info("Interrupted while listening, bye...")

    @staticmethod
    def _get_json_body(message):
        # parse JSON, mandatory attributes: id, name, creator, instructions
        try:
            return json.loads(message[1])
        except JSONDecodeError:
            return None


@contextmanager
def managed_recorder(create_recorder: Callable[[str], TelemetryRecorder], exp_id: str):
    r = create_recorder(exp_id)
    try:
        r.start()
        yield r
    finally:
        r.stop()

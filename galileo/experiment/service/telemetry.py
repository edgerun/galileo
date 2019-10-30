import logging

from symmetry.telemetry.recorder import TelemetryRecorder

from galileo.experiment.db import ExperimentDatabase
from galileo.experiment.model import Telemetry

logger = logging.getLogger(__name__)


class ExperimentTelemetryRecorder(TelemetryRecorder):

    # TODO: need locks?

    def __init__(self, rds, db: ExperimentDatabase, exp_id: str, flush_every=36) -> None:
        super().__init__(rds)
        self.db = db
        self.exp_id = exp_id

        self.flush_every = flush_every
        self.i = 0
        self.buffer = list()

    def run(self):
        try:
            logger.debug('starting ExperimentTelemetryRecorder for experiment %s', self.exp_id)
            super().run()
        finally:
            logger.debug('closing ExperimentTelemetryRecorder for experiment %s', self.exp_id)
            self._flush()

    def _record(self, timestamp, metric, node, value):
        try:
            val = float(value)
        except ValueError:
            # the rationale is that this block will be executed rarely, and checking each time may be more expensive
            # than having the try/except block
            if metric == 'status':
                val = 1 if value == 'true' else 0
            else:
                logger.error('Could not convert value "%s" of metric "%s"', value, metric)
                return

        self.buffer.append(Telemetry(float(timestamp), metric, node, val, self.exp_id))

        self.i = (self.i + 1) % self.flush_every
        if self.i == 0:
            self._flush()

    def _flush(self):
        if not self.buffer:
            return

        logger.debug('saving %s telemetry records of experiment "%s"', len(self.buffer), self.exp_id)

        self.db.save_telemetry(self.buffer)
        self.buffer.clear()

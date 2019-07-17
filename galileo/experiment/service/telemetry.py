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
            super().run()
        finally:
            self._flush()

    def _record(self, timestamp, metric, node, value):
        self.buffer.append(Telemetry(float(timestamp), metric, node, float(value), self.exp_id))

        self.i = (self.i + 1) % self.flush_every
        if self.i == 0:
            self._flush()

    def _flush(self):
        if not self.buffer:
            return

        logger.debug('saving %s traces to database', len(self.buffer))
        self.db.save_telemetry(self.buffer)
        self.buffer.clear()

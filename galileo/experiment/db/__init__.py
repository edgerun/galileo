import logging
from abc import ABC
from typing import List, Tuple

from galileo.experiment.model import Experiment, Instructions, Telemetry

logger = logging.getLogger(__name__)


class ExperimentDatabase(ABC):

    def open(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def save_experiment(self, experiment: Experiment):
        raise NotImplementedError

    def update_experiment(self, experiment: Experiment):
        raise NotImplementedError

    def get_experiment(self, exp_id: str) -> Experiment:
        raise NotImplementedError

    def save_traces(self, traces: List[Tuple]):
        """
        Saves multiple ServiceRequestTrace tuples.
        :param traces: a list of ServiceRequestTrace tuples
        :return:
        """
        raise NotImplementedError

    def touch_traces(self, experiment: Experiment):
        raise NotImplementedError

    def save_instructions(self, instructions: Instructions):
        raise NotImplementedError

    def get_instructions(self, exp_id: str) -> Instructions:
        raise NotImplementedError

    def save_telemetry(self, telemetry: List[Telemetry]):
        raise NotImplementedError

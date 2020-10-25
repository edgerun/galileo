import time
from abc import ABC
from typing import List

from galileodb import Experiment, ExperimentDatabase


class ExperimentService(ABC):

    def save(self, exp: Experiment) -> bool:
        raise NotImplementedError

    def find(self, exp_id: str):
        raise NotImplementedError

    def delete(self, exp_id: str):
        raise NotImplementedError

    def finalize_experiment(self, exp: Experiment, status):
        raise NotImplementedError

    def exists(self, exp_id: str) -> bool:
        raise NotImplementedError

    def find_all(self) -> List[Experiment]:
        raise NotImplementedError


class SimpleExperimentService(ExperimentService):

    def __init__(self, repository: ExperimentDatabase):
        self.repository = repository

    def save(self, exp: Experiment) -> bool:
        if not self.exists(exp.id):
            self.repository.save_experiment(exp)
            return True
        else:
            self.repository.update_experiment(exp)
            return False

    def find(self, exp_id: str):
        return self.repository.get_experiment(exp_id)

    def delete(self, exp_id: str):
        self.repository.delete_experiment(exp_id)

    def finalize_experiment(self, exp: Experiment, status):
        exp.status = status
        exp.end = time.time()
        self.repository.update_experiment(exp)
        self.repository.touch_traces(exp)

    def exists(self, exp_id) -> bool:
        return self.repository.get_experiment(exp_id) is not None

    def find_all(self):
        return self.repository.find_all()

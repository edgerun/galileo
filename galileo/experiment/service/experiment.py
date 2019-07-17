from abc import ABC

from galileo.experiment.db import ExperimentDatabase
from galileo.experiment.model import Experiment


class ExperimentService(ABC):

    def save(self, exp: Experiment) -> bool:
        raise NotImplementedError

    def save_json(self, json) -> (Experiment, bool):
        raise NotImplementedError

    def finish_experiment(self, exp: Experiment):
        raise NotImplementedError

    def exists(self, exp_id: str) -> bool:
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

    def save_json(self, json_body) -> (Experiment, bool):
        if not self.exists(json_body['id']):
            exp = Experiment(
                id=json_body['id'],
                creator=json_body['creator'],
                name=json_body['name'],
                status=json_body['status'],
            )

            saved = self.save(exp)
            return exp, saved
        else:
            return self.repository.get_experiment(json_body['id']), False

    def finish_experiment(self, exp: Experiment):
        exp.status = 'FINISHED'
        self.repository.update_experiment(exp)
        self.repository.touch_traces(exp)

    def exists(self, exp_id) -> bool:
        return self.repository.get_experiment(exp_id) is not None

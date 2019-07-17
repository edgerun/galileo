from abc import ABC
from typing import Optional

from galileo.experiment.db import ExperimentDatabase
from galileo.experiment.model import Instructions


class InstructionService(ABC):

    def save(self, ins: Instructions) -> None:
        raise NotImplementedError

    def find(self, exp_id: str) -> Instructions:
        raise NotImplementedError

    def save_json(self, exp_id, json_body) -> Instructions:
        raise NotImplementedError


class SimpleInstructionService(InstructionService):

    def __init__(self, repository: ExperimentDatabase):
        self.repository = repository

    def save(self, ins: Instructions) -> None:
        self.repository.save_instructions(ins)

    def save_json(self, exp_id, json_body) -> Instructions:
        ins = Instructions()
        ins.exp_id = exp_id
        ins.instructions = json_body['instructions']
        self.save(ins)
        return ins

    def find(self, exp_id: str) -> Optional[Instructions]:
        return self.repository.get_instructions(exp_id)

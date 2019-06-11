from typing import NamedTuple


class RegisterCommand(NamedTuple):
    pass


class InfoCommand(NamedTuple):
    pass


class RuntimeMetric(NamedTuple):
    host: str
    service: str
    metric: str
    value: float


class SpawnClientsCommand(NamedTuple):
    host: str
    service: str
    num: int


class SetRpsCommand(NamedTuple):
    host: str
    service: str
    rps: int


class CloseRuntimeCommand(NamedTuple):
    host: str
    service: str


class RegisterEvent(NamedTuple):
    host: str


class UnregisterEvent(NamedTuple):
    host: str

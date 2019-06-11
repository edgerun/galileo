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

    @staticmethod
    def channel(host: str):
        return 'galileo:spawn:%s' % host


class SetRpsCommand(NamedTuple):
    host: str
    service: str
    rps: float

    @staticmethod
    def channel(host: str):
        return 'galileo:rps:%s' % host


class CloseRuntimeCommand(NamedTuple):
    host: str
    service: str

    @staticmethod
    def channel(host: str):
        return 'galileo:rt_close:%s' % host


class RegisterEvent(NamedTuple):
    host: str


class UnregisterEvent(NamedTuple):
    host: str

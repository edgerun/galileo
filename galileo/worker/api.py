from typing import NamedTuple


class RegisterWorkerEvent(NamedTuple):
    name: str


class UnregisterWorkerEvent(NamedTuple):
    name: str


class RegisterWorkerCommand(NamedTuple):
    pass


class StartTracingCommand(NamedTuple):
    pass


class PauseTracingCommand(NamedTuple):
    pass


class ClientConfig(NamedTuple):
    service: str
    client: str = None
    parameters: dict = None


class ClientDescription(NamedTuple):
    client_id: str
    worker: str
    config: ClientConfig


class ClientInfo(NamedTuple):
    description: ClientDescription
    requests: int
    failed: int


class CloseClientCommand(NamedTuple):
    client_id: str


class CreateClientCommand(NamedTuple):
    host: str
    config: ClientConfig
    num: int = 1


class StopClientsCommand(NamedTuple):
    client_id: str


class ClientStartedEvent(NamedTuple):
    host: str
    client_id: str


class ClientStoppedEvent(NamedTuple):
    host: str
    client_id: str


class SetWorkloadCommand(NamedTuple):
    client_id: str
    num: int = None
    distribution: str = 'constant'
    parameters: tuple = None


class StopWorkloadCommand(NamedTuple):
    client_id: str


class WorkloadDoneEvent(NamedTuple):
    client_id: str

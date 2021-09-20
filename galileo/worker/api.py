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
    worker_labels: dict = None

    def __repr__(self):
        return self.__str__()

    def __str__(self) -> str:
        return 'ClientConfig(service={}, client={}, parameters={}, worker_labels:{})'.format(
            self.service, self.client, self._abbrv_parameters(self.parameters),
            self.worker_labels)

    def _abbrv_parameters(self, d):
        if d is None:
            return d

        s = str(d)
        if len(s) > 120:
            return s[:105] + ' <abbreviated> }'


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

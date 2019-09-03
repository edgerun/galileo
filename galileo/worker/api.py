import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)


class ClientConfig(NamedTuple):
    service: str
    client: str
    parameters: dict = None


class CreateClientGroupCommand(NamedTuple):
    """
    Create a new ClientGroup on the given host with the given config.
    """
    host: str
    cfg: ClientConfig
    gid: str = None


class CloseClientGroupCommand(NamedTuple):
    gid: str


class StartClientsCommand(NamedTuple):
    gid: str
    num: int = 1


class StopClientsCommand(NamedTuple):
    gid: str
    num: int = 1


class SetRpsCommand(NamedTuple):
    gid: str
    value: float
    dist: str = 'constant'
    args: tuple = None


class RegisterWorkerEvent(NamedTuple):
    name: str


class UnregisterWorkerEvent(NamedTuple):
    name: str


class RegisterWorkerCommand(NamedTuple):
    pass

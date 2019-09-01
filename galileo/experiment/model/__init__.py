from typing import NamedTuple, List


class Experiment:
    id: str
    name: str
    creator: str
    start: float
    end: float
    created: float
    status: str

    def __init__(self, id: str = None, name: str = None, creator: str = None, start: float = None, end: float = None,
                 created: float = None, status: str = None) -> None:
        super().__init__()
        self.id = id
        self.name = name
        self.creator = creator
        self.start = start
        self.end = end
        self.created = created
        self.status = status

    def __str__(self) -> str:
        return 'Experiment%s' % self.__dict__


class Instructions:
    exp_id: str
    instructions: str

    def __init__(self, exp_id=None, instructions=None):
        self.exp_id = exp_id
        self.instructions = instructions


class Telemetry(NamedTuple):
    timestamp: float
    metric: str
    node: str
    value: float
    exp_id: str


class WorkloadConfiguration(NamedTuple):
    service: str
    ticks: List[int]
    clients_per_host: int
    arrival_pattern: str
    client: str = None


class ExperimentConfiguration(NamedTuple):
    duration: int
    interval: int
    workloads: List[WorkloadConfiguration]


class ServiceRequestTrace(NamedTuple):
    client: str
    service: str
    host: str
    created: float
    sent: float
    done: float

    @property
    def rt_time(self):
        return (self.done - self.created) * 1000

    @property
    def queue_time(self):
        return (self.sent - self.created) * 1000

    @property
    def processing_time(self):
        return (self.done - self.sent) * 1000

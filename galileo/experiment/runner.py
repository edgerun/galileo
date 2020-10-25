import math
import time

from galileodb.model import ExperimentConfiguration

from galileo.controller import ClusterController
from galileo.shell.shell import Galileo


def run_experiment(ctrl: ClusterController, exp: ExperimentConfiguration):
    g = Galileo(ctrl)
    workload_clients = {}

    for workload in exp.workloads:
        workload_clients[workload] = g.spawn(workload.service, num=workload.clients_per_host, client=workload.client,
                                             parameters=workload.client_parameters)

    ticks = int(math.ceil(exp.duration / exp.interval))

    for t in range(ticks):
        for workload, clients in workload_clients.items():
            service_rps = workload.ticks[t]
            clients.rps(service_rps / workload.clients_per_host)

        time.sleep(exp.interval)

    for clients in workload_clients.values():
        clients.rps(0)

    for clients in workload_clients.values():
        clients.close()

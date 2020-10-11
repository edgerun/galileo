import math
import time

from galileodb.model import ExperimentConfiguration

from galileo.controller import RedisClusterController
from galileo.shell.shell import Galileo


def run_experiment(rds, exp: ExperimentConfiguration):
    g = Galileo(RedisClusterController(rds))

    workload_clients = {}

    for workload in exp.workloads:
        workload_clients[workload] = g.spawn(workload.service, num=workload.clients_per_host, client=workload.client,
                                             client_parameters=workload.client_parameters)

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

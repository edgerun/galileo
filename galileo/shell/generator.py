"""
Tools to generate galileo shell scripts.

TODO: rethink whether this is necessary with the new python shell
"""

import math
from typing import List

from galileodb.model import ExperimentConfiguration


def generate_script(cfg: ExperimentConfiguration, *args, **kwargs) -> List[str]:
    commands = list()

    if cfg.interval <= 0:
        raise ValueError('interval has to be a non-zero positive integer')

    for wl_id, workload in enumerate(cfg.workloads):
        # TODO: client, client_parameters
        commands.append(f"wl_{wl_id} = g.spawn('{workload.service}', {workload.clients_per_host})")

    ticks = int(math.ceil(cfg.duration / cfg.interval))

    for t in range(ticks):
        for wl_id, workload in enumerate(cfg.workloads):
            service_rps = workload.ticks[t]
            commands.append(f'wl_{wl_id}.rps({service_rps}/{workload.clients_per_host})')

        commands.append(f'sleep({cfg.interval})')

    for wl_id, workload in enumerate(cfg.workloads):
        commands.append(f'wl_{wl_id}.rps(0)')

    for wl_id, workload in enumerate(cfg.workloads):
        commands.append(f'wl_{wl_id}.close()')

    return commands

import json
import math
from concurrent.futures.thread import ThreadPoolExecutor
from typing import List

from galileodb.model import ExperimentConfiguration
from symmetry.common.shell import Shell, parsed, ArgumentError, print_tabular

from galileo.controller.controller import ExperimentController


class ExperimentShell(Shell):
    intro = 'Welcome to the interactive galileo Shell.'
    prompt = 'galileo> '

    controller = None

    def __init__(self, controller: ExperimentController, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.controller = controller

    def preloop(self):
        if not self.controller:
            raise RuntimeError('Controller not set')

        self.controller.discover()

    @parsed
    def do_workers(self, pattern: str = ''):
        try:
            for worker in self.controller.list_workers(pattern):
                self.println(worker)
        except ValueError as e:
            raise ArgumentError(e)

    @parsed
    def do_client_groups(self, worker: str):
        infos = self.controller.client_group_info()

        if worker:
            for info in infos:
                if info['worker'] == worker:
                    self.println(info['gid'])
        else:
            for worker in self.controller.list_workers():
                self.println('worker:', worker)
                for info in infos:
                    if info['worker'] == worker:
                        self.println('  ', info['gid'])

    @parsed
    def do_info(self):
        print_tabular(self.controller.client_group_info(), printer=self.println)

    @parsed
    def do_discover(self):
        self.controller.discover()

    @parsed
    def do_logging(self, status: str):
        """
        Turn trace logging of workers on/off.

        :param status: 'on' or 'off'
        """
        if status == 'on' or status == 'off':
            self.controller.set_trace_logging(status)
        else:
            self.println("Wrong input, must be 'on' or 'off'.")

    @parsed
    def do_ping(self):
        result = self.controller.ping()
        for worker in result:
            self.println(worker)

    @parsed
    def do_spawn(self, worker_pattern, service, num: int = 1, client: str = '', client_parameters: str = '{}'):
        """
        Spawn a new client for the given service on the given worker.

        :param worker_pattern: the worker name or pattern (e.g., 'pico1' or 'pico[0-9]')
        :param service: the service name
        :param num: the number of clients
        :param client: the client app name (optional, if not given will use service name)
        :param client_parameters: parameters for the app (optional, e.g.: '{ "size": "small" }'
        """

        def spawn_client(worker):
            try:
                parameters = json.loads(client_parameters)
                gid = self.controller.spawn_client(worker, service, num, client if client else None,
                                                   parameters=parameters)
                self.println('%s: OK (%s)' % (worker, gid))
                return gid
            except Exception as ex:
                self.println('%s: ERROR (%s)' % (worker, str(ex)))
                return None

        try:
            with ThreadPoolExecutor(max_workers=8) as executor:
                workers = self.controller.list_workers(worker_pattern)
                self.println('spawning clients on %d workers' % len(workers))
                for _ in executor.map(spawn_client, workers):
                    pass  # iterator blocks until all are commands have returned

        except ValueError as e:
            raise ArgumentError(e)

    @parsed
    def do_rps(self, worker_pattern, service, rps: float, client: str = ''):
        try:
            for worker in self.controller.list_workers(worker_pattern):
                self.controller.set_rps(worker, service, rps, client if client else None)
        except ValueError as e:
            raise ArgumentError(e)

    @parsed
    def do_close(self, worker_pattern, service, client: str = ''):
        try:
            for worker in self.controller.list_workers(worker_pattern):
                self.controller.close_runtime(worker, service, client if client else None)
        except ValueError as e:
            raise ArgumentError(e)


def create_instructions(cfg: ExperimentConfiguration, workers: List[str]) -> List[str]:
    commands = list()

    if cfg.interval <= 0:
        raise ValueError('interval has to be a non-zero positive integer')

    for workload in cfg.workloads:
        for worker in workers:
            if workload.client:
                if workload.client_parameters:
                    client_parameters = json.dumps(workload.client_parameters)
                    commands.append(
                        f"spawn {worker} {workload.service} {workload.clients_per_host} {workload.client} '{client_parameters}'")
                else:
                    commands.append(f"spawn {worker} {workload.service} {workload.clients_per_host} {workload.client}")

            else:
                commands.append(f'spawn {worker} {workload.service} {workload.clients_per_host}')

    ticks = int(math.ceil(cfg.duration / cfg.interval))

    for t in range(ticks):
        for workload in cfg.workloads:
            service_rps = workload.ticks[t]
            worker_rps = [0] * len(workers)

            # distribute service rps across workers
            for i in range(service_rps):
                worker_rps[i % len(workers)] += 1

            for i in range(len(workers)):
                if workload.client:
                    commands.append(f'rps {workers[i]} {workload.service} {worker_rps[i]} {workload.client}')
                else:
                    commands.append(f'rps {workers[i]} {workload.service} {worker_rps[i]}')

        commands.append('sleep %d' % cfg.interval)

    for workload in cfg.workloads:
        for worker in workers:
            if workload.client:
                commands.append(f'rps {worker} {workload.service} 0 {workload.client}')
            else:
                commands.append(f'rps {worker} {workload.service} 0')
    for workload in cfg.workloads:
        for worker in workers:
            if workload.client:
                commands.append(f'close {worker} {workload.service} {workload.client}')
            else:
                commands.append(f'close {worker} {workload.service}')

    return commands
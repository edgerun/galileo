import json
import logging
import math
import re
import sre_constants
import time
from typing import List

import pymq
import redis
from redis import WatchError
from symmetry.common.shell import Shell, parsed, ArgumentError, print_tabular

from galileo.experiment.model import Experiment, ExperimentConfiguration
from galileo.worker.api import CreateClientGroupCommand, CloseClientGroupCommand, ClientConfig, RegisterWorkerEvent, \
    UnregisterWorkerEvent, RegisterWorkerCommand, SetRpsCommand, StartClientsCommand

logger = logging.getLogger(__name__)


class ExperimentController:
    queue_key = 'galileo:experiments:queue'
    worker_key = 'galileo:workers'

    def __init__(self, rds: redis.Redis = None) -> None:
        super().__init__()
        self.rds = rds or redis.Redis(decode_responses=True)
        self.pubsub = None
        self.infos = list()

        pymq.subscribe(self._on_register_host)
        pymq.subscribe(self._on_unregister_host)

    def queue(self, config: ExperimentConfiguration, exp: Experiment = None):
        """
        Queues an experiment for the experiment daemon to load.
        :param config: experiment configuration
        :param exp: the experiment metadata (optional, as all parameters could be generated)
        :return:
        """
        message = exp.__dict__ if exp else dict()

        hosts = list(self.list_hosts())
        if not hosts:
            raise ValueError('No hosts to execute the experiment on')

        message['instructions'] = '\n'.join(create_instructions(config, hosts))
        logger.debug('queuing experiment data: %s', message)
        self.rds.lpush(ExperimentController.queue_key, json.dumps(message))

    def cancel(self, exp_id: str) -> bool:
        try:
            with self.rds.pipeline() as pipe:
                pipe.watch(ExperimentController.queue_key)
                workloads = pipe.lrange(ExperimentController.queue_key, 0, -1)
                pipe.multi()
                index = -1
                for idx, entry in enumerate(workloads):
                    body = json.loads(entry)
                    if body['id'] == exp_id:
                        index = idx
                if index == -1:
                    return False

                pipe.lset(ExperimentController.queue_key, index, 'DELETE')
                pipe.lrem(ExperimentController.queue_key, 1, 'DELETE')
                pipe.execute()
                return True
        except WatchError:
            # TODO maybe retry here and break out after too many retries
            logger.warning('WatchError cancelling experiment with id ' + exp_id)
            raise CancelError

    def ping(self):
        pymq.publish(RegisterWorkerCommand())

    def info(self):
        raise NotImplementedError  # TODO: create new info command

    def get_infos(self):
        return self.infos

    def list_hosts(self, pattern: str = ''):
        hosts = self.rds.smembers(self.worker_key)

        if not pattern:
            return hosts

        try:
            return [host for host in hosts if re.search('^%s$' % pattern, host)]
        except sre_constants.error as e:
            raise ValueError('Invalid pattern %s: %s' % (pattern, e))

    def list_clients(self, host):
        return self.rds.smembers('galileo:clients:%s' % host)

    def spawn_client(self, host, service, num):
        # FIXME: split into create/spawn command
        pymq.publish(CreateClientGroupCommand(host, ClientConfig(service, service)))
        time.sleep(1)
        pymq.publish(StartClientsCommand(f'{host}:{service}:{service}', num))

    def set_rps(self, host, service, rps):
        return pymq.publish(SetRpsCommand(f'{host}:{service}:{service}', rps))

    def close_runtime(self, host, service):
        return pymq.publish(CloseClientGroupCommand(f'{host}:{service}:{service}'))

    def _on_register_host(self, event: RegisterWorkerEvent):
        self.rds.sadd('galileo:workers', event.name)

    def _on_unregister_host(self, event: UnregisterWorkerEvent):
        self.rds.srem('galileo:workers', event.name)
        self.rds.delete('galileo:clients:%s' % event.name)

    def _on_unregister_client(self, host, client):
        self.rds.srem('galileo:clients:%s' % host, client)


class ExperimentShell(Shell):
    intro = 'Welcome to the interactive experiment controller Shell.'
    prompt = 'exp> '

    controller = None

    def __init__(self, controller: ExperimentController, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.controller = controller

    def preloop(self):
        if not self.controller:
            raise RuntimeError('Controller not set')

    @parsed
    def do_hosts(self, pattern: str = ''):
        try:
            for host in self.controller.list_hosts(pattern):
                self.println(host)
        except ValueError as e:
            raise ArgumentError(e)

    def do_clients(self, host):
        if host:
            for client in self.controller.list_clients(host):
                self.println(client)
        else:
            for host in self.controller.list_hosts():
                self.println('host:', host)
                for client in self.controller.list_clients(host):
                    self.println(' ', client)

    @parsed
    def do_info(self):
        self.controller.info()
        time.sleep(0.5)  # FIXME
        print_tabular(self.controller.get_infos(), printer=self.println)

    @parsed
    def do_ping(self):
        self.controller.ping()

    @parsed
    def do_spawn(self, host_pattern, service, num: int = 1):
        """
        Spawn a new client for the given service on the given host.

        :param host_pattern: the host name or pattern (e.g., 'pico1' or 'pico[0-9]')
        :param service: the service name
        :param num: the number of clients
        """
        try:
            for host in self.controller.list_hosts(host_pattern):
                self.controller.spawn_client(host, service, num)
        except ValueError as e:
            raise ArgumentError(e)

    @parsed
    def do_rps(self, host_pattern, service, rps: float):
        try:
            for host in self.controller.list_hosts(host_pattern):
                self.controller.set_rps(host, service, rps)
        except ValueError as e:
            raise ArgumentError(e)

    @parsed
    def do_close(self, host_pattern, service):
        try:
            for host in self.controller.list_hosts(host_pattern):
                self.controller.close_runtime(host, service)
        except ValueError as e:
            raise ArgumentError(e)


def create_instructions(cfg: ExperimentConfiguration, hosts: List[str]) -> List[str]:
    commands = list()

    for workload in cfg.workloads:
        for host in hosts:
            commands.append(f'spawn {host} {workload.service} {workload.clients_per_host}')

    ticks = int(math.ceil(cfg.duration / cfg.interval))

    for t in range(ticks):
        for workload in cfg.workloads:
            service_rps = workload.ticks[t]
            host_rps = [0] * len(hosts)

            # distribute service rps across hosts
            for i in range(service_rps):
                host_rps[i % len(hosts)] += 1

            for i in range(len(hosts)):
                commands.append(f'rps {hosts[i]} {workload.service} {host_rps[i]}')

        commands.append('sleep %d' % cfg.interval)

    for workload in cfg.workloads:
        for host in hosts:
            commands.append(f'rps {host} {workload.service} 0')
    for workload in cfg.workloads:
        for host in hosts:
            commands.append(f'close {host} {workload.service}')

    return commands


class CancelError(Exception):
    pass

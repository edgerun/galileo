import re
import sre_constants
import time

import redis

import symmetry.eventbus as eventbus
from galileo.event import RegisterCommand, InfoCommand, RegisterEvent, UnregisterEvent, SpawnClientsCommand, \
    RuntimeMetric, CloseRuntimeCommand, SetRpsCommand
from symmetry.common.shell import Shell, parsed, ArgumentError, print_tabular


class ExperimentController:

    def __init__(self, rds: redis.Redis = None) -> None:
        super().__init__()
        self.rds = rds or redis.Redis(decode_responses=True)
        self.pubsub = None
        self.infos = list()

        eventbus.listener(self._on_register_host)
        eventbus.listener(self._on_unregister_host)
        eventbus.listener(self._on_info)

    def ping(self):
        eventbus.publish(RegisterCommand())

    def info(self):
        self.infos.clear()
        eventbus.publish(InfoCommand())

    def get_infos(self):
        return self.infos

    def list_hosts(self, pattern: str = ''):
        hosts = self.rds.smembers('exp:hosts')

        if not pattern:
            return hosts

        try:
            return [host for host in hosts if re.search('^%s$' % pattern, host)]
        except sre_constants.error as e:
            raise ValueError('Invalid pattern %s: %s' % (pattern, e))

    def list_clients(self, host):
        return self.rds.smembers('exp:clients:%s' % host)

    def spawn_client(self, host, service, num):
        return eventbus.publish(SpawnClientsCommand(host, service, num), SpawnClientsCommand.channel(host))

    def set_rps(self, host, service, rps):
        return eventbus.publish(SetRpsCommand(host, service, rps), SetRpsCommand.channel(host))

    def close_runtime(self, host, service):
        return eventbus.publish(CloseRuntimeCommand(host, service), CloseRuntimeCommand.channel(host))

    def _on_register_host(self, event: RegisterEvent):
        self.rds.sadd('exp:hosts', event.host)

    def _on_unregister_host(self, event: UnregisterEvent):
        self.rds.srem('exp:hosts', event.host)
        self.rds.delete('exp:clients:%s' % event.host)

    def _on_unregister_client(self, host, client):
        self.rds.srem('exp:clients:%s' % host, client)

    def _on_info(self, event: RuntimeMetric):
        self.infos.append(event._asdict())


class ControllerShell(Shell):
    intro = 'Welcome to the interactive experiment controller Shell.'
    prompt = 'exp> '

    controller = None
    controller_thread = None

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
import re
import sre_constants
import threading
import time

import redis

from symmetry.common.shell import Shell, parsed, ArgumentError, print_tabular


class ExperimentController:

    def __init__(self, rds: redis.Redis = None) -> None:
        super().__init__()
        self.rds = rds or redis.Redis(decode_responses=True)
        self.pubsub = None
        self.infos = list()

    def ping(self):
        self.rds.publish('exp/ping', 1)

    def info(self):
        self.infos.clear()
        self.rds.publish('exp/info', 1)

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
        return self.rds.publish('exp/spawn/%s/%s' % (host, service), num)

    def set_rps(self, host, service, rps):
        return self.rds.publish('exp/rps/%s/%s' % (host, service), rps)

    def close_runtime(self, host, service):
        return self.rds.publish('exp/close/%s' % host, service)

    def run(self):
        self.pubsub = self.rds.pubsub()

        try:
            self.pubsub.subscribe(['exp/register/host', 'exp/unregister/host'])
            self.pubsub.psubscribe(['exp/register/client/*', 'exp/unregister/client/*', 'exp/info/*'])

            self.ping()  # request all running clients to register themselves

            for event in self.pubsub.listen():
                if event['type'] not in ['message', 'pmessage']:
                    continue

                self._on_event(event['channel'], event['data'])
        except Exception as e:
            print('caught exception', type(e), e)
        finally:
            self.pubsub.close()

    def _on_event(self, channel, data):
        if channel == 'exp/register/host':
            self._on_register_host(data)
        elif channel == 'exp/unregister/host':
            self._on_unregister_host(data)
        elif channel.startswith('exp/register/client/'):
            host = channel.split('/')[3]
            self._on_register_client(host, data)
        elif channel.startswith('exp/unregister/client/'):
            host = channel.split('/')[3]
            self._on_unregister_client(host, data)
        elif channel.startswith('exp/info/'):
            _, _, host, service, metric = channel.split('/')
            self._on_info(host, service, metric, data)

    def _on_register_host(self, host):
        self.rds.sadd('exp:hosts', host)

    def _on_unregister_host(self, host):
        self.rds.srem('exp:hosts', host)
        self.rds.delete('exp:clients:%s' % host)

    def _on_register_client(self, host, client):
        self.rds.sadd('exp:clients:%s' % host, client)

    def _on_unregister_client(self, host, client):
        self.rds.srem('exp:clients:%s' % host, client)

    def _on_info(self, host, service, metric, data):
        self.infos.append({
            'host': host,
            'service': service,
            'metric': metric,
            'value': data
        })

    def close(self):
        self.pubsub.unsubscribe()
        self.pubsub.punsubscribe()


class ControllerShell(Shell):
    intro = 'Welcome to the interactive experiment controller Shell.'
    prompt = 'exp> '

    controller = None
    controller_thread = None

    def __init__(self, controller: ExperimentController, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.controller = controller

    def _start(self):
        if not self.controller:
            raise RuntimeError('Controller not set')

        self.controller_thread = threading.Thread(target=self.controller.run)
        self.controller_thread.start()

    def _close(self):
        if self.controller:
            self.controller.close()
            self.controller_thread.join()

    def preloop(self):
        self._start()

    def postloop(self):
        self._close()

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

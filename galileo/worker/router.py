import abc
import logging
import time

import requests
from symmetry.service.routing import Balancer, StaticLocalhostBalancer

logger = logging.getLogger(__name__)


# TODO: probably belongs into symmetry

class ServiceRequest:

    def __init__(self, payload, service: str = None) -> None:
        super().__init__()
        self.payload = payload
        self.service = service
        self.host = None
        self.time_created = time.time()
        self.time_sent = None
        self.time_done = None
        self.client_id = None


class Service(abc.ABC):
    def request(self, host, request: ServiceRequest, timeout=None) -> requests.Response:
        raise NotImplementedError()


class ServiceRegistry:

    def __init__(self) -> None:
        super().__init__()
        self.registry = dict()

    def register(self, name, service: Service):
        self.registry[name] = service

    def service(self, name) -> Service:
        return self.registry[name]


class ServiceRequestException(Exception):

    def __init__(self, request: ServiceRequest, cause: Exception, *args) -> None:
        super().__init__(*args)
        self.request = request
        self.cause = cause


class Router:
    retry = 5
    timeout = 1

    def __init__(self, registry: ServiceRegistry = None, balancer: Balancer = None) -> None:
        super().__init__()
        self.registry = registry or ServiceRegistry()
        self.balancer = balancer or StaticLocalhostBalancer()
        self.balancers = dict()

    def _get_balancer(self, service):
        if service not in self.balancers:
            self.balancers[service] = self.balancer.gen(service)

        return self.balancers[service]

    def request(self, request: ServiceRequest):
        # request -> http://<node>:service-port/service-endpoint
        # balance -> http://host/service-endpoint
        # build and run HTTP request

        service = self.registry.service(request.service)
        bal = self._get_balancer(request.service)

        attempt = 0
        while True:
            try:
                host, time_sent = next(bal), time.time()

                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('making service request attempt %d to host %s: %s', attempt + 1, host, request)

                response = service.request(host, request, timeout=self.timeout)
                request.host, request.time_sent, request.time_done = host, time_sent, time.time()
                return response
            except Exception as e:
                logger.info('Exception while sending request %s, %s: %s', request, type(e), e)
                print(e)
                attempt += 1
                if attempt >= self.retry:
                    raise ServiceRequestException(request, e, 'Gave up sending request after %d retries' % attempt)
                else:
                    continue

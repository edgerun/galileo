import abc
import logging
import time
import requests

from galileo.routing.balancer import Balancer

logger = logging.getLogger(__name__)


class ServiceRequest:
    service: str
    path: str
    method: str
    kwargs: dict

    created: float
    sent: float
    done: float

    def __init__(self, service, path='/', method='get', **kwargs) -> None:
        super().__init__()
        self.service = service
        self.path = path
        self.method = method
        self.kwargs = kwargs

        self.created = time.time()


class Router(abc.ABC):

    def request(self, req: ServiceRequest) -> requests.Response:
        url = self._get_url(req)

        logger.debug('forwarding request %s %s', req.method, url)

        req.sent = time.time()
        response = requests.request(req.method, url, **req.kwargs)
        req.done = req.sent

        logger.debug('%s %s: %s', req.method, url, response.status_code)
        return response

    def _get_url(self, req: ServiceRequest) -> str:
        raise NotImplementedError


class StaticRouter(Router):
    """
    Routes a request statically to <path_prefix>/<request_path>, so StaticRouter('http://localhost:8080/') would route
    everything to a webserver on localhost:8080.
    """

    def __init__(self, path_prefix) -> None:
        super().__init__()
        self.path_prefix = path_prefix

    def _get_url(self, req: ServiceRequest) -> str:
        return f'{self.path_prefix}{req.path}'


class DynamicRouter(Router, abc.ABC):
    """
    Abstract base class for routing using a balancer.
    """
    _balancer: Balancer

    def __init__(self, balancer: Balancer) -> None:
        super().__init__()
        self._balancer = balancer

    def _get_url(self, req: ServiceRequest) -> str:
        host = self._balancer.next_host(req.service)
        return self._create_url(host, req)

    def _create_url(self, host, req: ServiceRequest):
        raise NotImplementedError


class HostRouter(DynamicRouter):
    """
    Routes a service request to http://<host>/<request_path> using a balancer. This is useful for testing without
    requiring a symmetry proxy on each mc2 node for routing to the correct container.
    """

    def _create_url(self, host, req: ServiceRequest):
        return f'http://{host}{req.path}'


class ServiceRouter(DynamicRouter):
    """
    Routes a service request to http://<host>/<service>/<request_path> using a balancer. This assumes a setup where each
    mc2 node has a reverse proxy that routes requests to the correct app container.
    """

    def _create_url(self, host, req: ServiceRequest) -> str:
        return f'http://{host}/{req.service}{req.path}'

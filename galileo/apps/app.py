import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)


class AppRequest(NamedTuple):
    app_name: str
    method: str
    endpoint: str
    kwargs: dict


class AppClient:

    def __init__(self, name, context, module) -> None:
        super().__init__()
        self.name = name
        self.context = context
        self.module = module

    def __getattr__(self, item):
        return getattr(self.module, item)

    def next_request(self) -> AppRequest:
        method, endpoint, kwargs = self.module.next_request()
        return AppRequest(self.name, method, endpoint, kwargs or {})


class DefaultAppClient(AppClient):
    """
    The default app client is a flexible http request client. It only requires the client parameters which are used as
    follows: parameters['method'] holds the HTTP method to use (defaults to 'get'), parameters['path'] holds the path to
    which the request is sent (defaults to '/'), and parameters['kwargs'] holds a dict with keyword arguments passed to
    the python requests library when performing the `request` call (e.g., 'data': ..., 'json', ...).
    """

    def __init__(self, parameters=None) -> None:
        if parameters:
            method = parameters.get('method', 'get')
            path = parameters.get('path', '/')
            kwargs = parameters.get('kwargs')
        else:
            method = 'get'
            path = '/'
            kwargs = None

        client = HttpClient(method, path, kwargs)

        super().__init__('http', None, client)


class HttpClient:
    def __init__(self, method='get', path='/', parameters=None) -> None:
        super().__init__()
        self.method = method
        self.path = path
        self.parameters = parameters or {}

    def next_request(self):
        return self.method, self.path, self.parameters

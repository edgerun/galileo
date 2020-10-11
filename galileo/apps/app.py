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


class HttpClient:
    def __init__(self, method='get', path='/', parameters=None) -> None:
        super().__init__()
        self.method = method
        self.path = path
        self.parameters = parameters or {}

    def next_request(self):
        return self.method, self.path, self.parameters

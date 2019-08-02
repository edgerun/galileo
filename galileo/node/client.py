import abc
import logging
import os

import requests

from galileo.node.router import Service, ServiceRequest
from galileo.util import read_file

logger = logging.getLogger(__name__)


class RequestFactory(abc.ABC):
    def create_request(self) -> ServiceRequest:
        raise NotImplementedError()


class ExperimentService:

    def __init__(self, name, request_factory: RequestFactory) -> None:
        super().__init__()
        self.name = name
        self.request_factory = request_factory.create_request


class ImageClassificationRequestFactory(RequestFactory):

    def __init__(self, service, image_directory) -> None:
        super().__init__()
        self.service = service
        self.images = self.load_images(image_directory)
        self.i = 0

    def create_request(self) -> ServiceRequest:
        r = ServiceRequest(self.images[self.i], self.service)
        self.i = (self.i + 1) % len(self.images)
        return r

    @staticmethod
    def load_images(path):
        """
        Loads all jpegs from the given path and prepares them for a `requests` POST request.
        """
        if not os.path.exists(path):
            logger.warning('path to images %s does not exist, cannot produce requests', os.path.abspath(path))
            return []
        jpegs = [f for f in os.listdir(path) if f.endswith(".jpg") or f.endswith(".jpeg")]
        # prepares file for the format needed for POST requests
        images = [{'name': f, 'data': read_file(os.path.join(path, f))} for f in jpegs]
        # print("Loaded %d images" % len(images))
        return images


class MXNetImageClassifierService(Service):

    def __init__(self, model: str) -> None:
        super().__init__()
        self.model = model

    def request(self, host, request: ServiceRequest, timeout=None):
        url = 'http://' + host + ':8080/predictions/' + self.model

        file_name = request.payload['name']
        file_data = request.payload['data']

        return requests.post(url, files={'data': (file_name, file_data)}, timeout=timeout)

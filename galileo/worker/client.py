import abc
import logging
import os

from symmetry.gateway import ServiceRequest

from galileo.util import read_file

logger = logging.getLogger(__name__)


# TODO: should be a plugin mechanism (`galileo register-client ./dir-containing-code/')

class RequestFactory(abc.ABC):
    def create_request(self) -> ServiceRequest:
        raise NotImplementedError()


class ClientEmulator:

    def __init__(self, name, request_factory: RequestFactory) -> None:
        super().__init__()
        self.name = name
        self.request_factory = request_factory.create_request


class ImageClassificationRequestFactory(RequestFactory):

    def __init__(self, model, image_directory, service='mxnet-model-server') -> None:
        super().__init__()
        self.model = model
        self.image_directory = image_directory
        self.service = service
        self._request_generator = self._requestgen()

    def _requestgen(self):
        images = self.load_images(self.image_directory)
        model = self.model
        service = self.service

        n = len(images)

        i = 0
        while True:
            payload = images[i]
            kwargs = {'files': {'data': (payload['name'], payload['data'])}}
            yield ServiceRequest(service, f'/predictions/{model}', method='post', **kwargs)
            i = (i + 1) % n

    def create_request(self) -> ServiceRequest:
        return next(self._request_generator)

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

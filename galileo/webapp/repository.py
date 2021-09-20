import logging
import os
import tempfile

import falcon

from galileo.apps.repository import Repository, RepositoryException

logger = logging.getLogger(__name__)


class RepositoryResource:
    repo: Repository

    def __init__(self, repo: Repository) -> None:
        super().__init__()
        self.repo = repo

    def on_get(self, req, resp):
        resp.media = [{'name': app.name, 'manifest': app.manifest} for app in self.repo.list_apps()]

    def on_get_info(self, req, resp, app_name):
        app = self.repo.get_app(app_name)
        if not app:
            raise falcon.HTTPNotFound()

        resp.media = {'name': app.name, 'manifest': app.manifest}

    def on_delete_info(self, req, resp, app_name):
        resp.media = self.repo.delete_app(app_name)

    def on_post(self, req: falcon.Request, resp: falcon.Response):
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, 'app.zip')

            with open(zip_path, 'wb') as fd:
                fd.write(req.stream.read())

            try:
                app = self.repo.add(zip_path)
            except RepositoryException as e:
                raise falcon.HTTPBadRequest('Error processing upload', str(e))

        resp.status = falcon.HTTP_201
        resp.media = {'name': app.name, 'manifest': app.manifest}

    def on_get_download(self, req, resp: falcon.Response, app_name):
        app = self.repo.get_app(app_name)
        if not app:
            raise falcon.HTTPNotFound()

        resp.content_type = 'application/zip'
        with open(app.archive_path, 'rb') as fd:
            resp.body = fd.read()

        resp.downloadable_as = app.archive_path.split('/')[-1]

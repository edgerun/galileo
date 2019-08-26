import logging
import os
import tempfile
import zipfile
from typing import List, Optional

import falcon
import requests
import yaml

from galileo.apps import AppInfo

logger = logging.getLogger(__name__)


class Repository:
    repo_path: str

    def __init__(self, path) -> None:
        super().__init__()
        self.repo_path = path

    def get_app(self, app_name) -> Optional[AppInfo]:
        for app in self.list_apps():
            if app.name == app_name:
                return app

    def list_apps(self) -> List[AppInfo]:
        archives = self.list_archives()

        modules = list()
        for archive in archives:
            manifest = self._get_manifest(archive)
            if not manifest:
                continue

            if 'name' not in manifest:
                logger.debug('archive contains no manifest: %s', archive)
                continue

            info = AppInfo(manifest['name'], manifest, archive)
            modules.append(info)

        return modules

    def list_archives(self):
        return [os.path.join(self.repo_path, f) for f in os.listdir(self.repo_path) if f.endswith('.zip')]

    def _open_archive(self, archive):
        return zipfile.ZipFile(archive, 'r')

    def _get_manifest(self, archive):
        try:
            with self._open_archive(archive) as zf:
                try:
                    zf.getinfo('manifest.yml')
                except KeyError:
                    return

                read = zf.read('manifest.yml')
                y = yaml.safe_load(read)
                return y
        except zipfile.BadZipFile:
            return None


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

    def on_get_download(self, req, resp: falcon.Response, app_name):
        app = self.repo.get_app(app_name)
        if not app:
            raise falcon.HTTPNotFound()

        resp.content_type = 'application/zip'
        with open(app.archive_path, 'rb') as fd:
            resp.body = fd.read()

        resp.downloadable_as = app.archive_path.split('/')[-1]


class RepositoryClient:
    repo_host = 'http://localhost:5001'
    repo_endpoint = '/api/apps'

    def __init__(self, repo_host, repo_endpoint=None) -> None:
        super().__init__()
        self.repo_host = repo_host

        if repo_endpoint:
            self.repo_endpoint = repo_endpoint

    def exists(self, app_name) -> bool:
        resp = requests.get(self.app_url(app_name))
        if resp.status_code == 404:
            return False

        logger.debug(resp.json())
        if resp.json()['name'] == app_name:
            return True

        return False

    @property
    def repo_url(self):
        return self.repo_host + self.repo_endpoint

    def app_url(self, app_name):
        return self.repo_url + '/' + app_name

    def list(self) -> List[AppInfo]:
        response = requests.get(self.repo_url)

        apps = response.json()

        return [AppInfo(app['name'], app['manifest']) for app in apps]

    def download_app(self, app_name, directory):
        resp = requests.get(self.app_url(app_name) + '/download')

        logger.debug('processing download response for %s %s', app_name, resp)
        resp.raise_for_status()

        with tempfile.TemporaryFile() as tmp:
            tmp.write(resp.content)
            tmp.seek(0)

            with zipfile.ZipFile(tmp) as zfd:
                logger.debug('extracting %s to %s', app_name, directory)
                zfd.extractall(directory + '/' + app_name)

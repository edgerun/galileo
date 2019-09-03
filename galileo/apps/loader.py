import abc
import importlib.util
import logging
import os
from typing import List

import yaml

from galileo.apps import AppInfo, Context
from galileo.apps.app import AppClient
from galileo.apps.repository import RepositoryClient

logger = logging.getLogger(__name__)


class AppClientLoader(abc.ABC):
    def list(self) -> List[AppInfo]:
        raise NotImplementedError

    def load(self, name, parameters=None) -> AppClient:
        raise NotImplementedError


class AppClientDirectoryLoader(AppClientLoader):
    _manifest_file = 'manifest.yml'
    _module_file = 'generator.py'

    root: str

    def __init__(self, root: str) -> None:
        super().__init__()
        self.root = root

    def list(self) -> List[AppInfo]:
        root = self.root
        manifest_file = self._manifest_file

        result = list()
        for d in os.listdir(root):
            manifest_path = os.path.join(root, d, manifest_file)
            if not os.path.exists(manifest_path):
                continue

            try:
                manifest = self._load_manifest(manifest_path)
                try:
                    self._validate_manifest(manifest)
                except ValueError as e:
                    logger.debug('Error validating manifest: %s', e)
                    continue

                app_info = AppInfo(manifest['name'], manifest)
                result.append(app_info)
            except:
                logger.exception('Exception loading app manifest %s', manifest_path)

        return result

    def load(self, name, parameters=None) -> AppClient:
        manifest = self._require_manifest(name)
        spec, module = self._require_module(name)

        context = Context()
        context.path = os.path.join(self.root, name)
        context.name = name
        context.manifest = manifest
        context.parameters = parameters or dict()

        module.context = context

        spec.loader.exec_module(module)

        return AppClient(name, context, module)

    def _require_module(self, name):
        module_path = os.path.join(self.root, name, self._module_file)
        spec = importlib.util.spec_from_file_location('galileo.clients.' + name, module_path)
        module = importlib.util.module_from_spec(spec)
        return spec, module

    def _require_manifest(self, name):
        manifest_path = os.path.join(self.root, name, self._manifest_file)
        if not os.path.exists(manifest_path):
            raise ValueError('No manifest.yml found in %s' % manifest_path)

        manifest = self._load_manifest(manifest_path)
        self._validate_manifest(manifest)
        return manifest

    def _load_manifest(self, file):
        with open(file) as fd:
            return yaml.safe_load(fd)

    def _validate_manifest(self, manifest):
        if 'name' not in manifest:
            raise ValueError('Manifest error: no app name specified')


class AppRepositoryFallbackLoader(AppClientLoader):
    loader: AppClientDirectoryLoader
    repo: RepositoryClient

    def __init__(self, loader, repo) -> None:
        super().__init__()
        self.loader = loader
        self.repo = repo

    def list(self) -> List[AppInfo]:
        try:
            apps = {info.name: info for info in self.repo.list()}
        except IOError:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception('Error getting list from app repository')
            apps = {}

        for app in self.loader.list():
            # we prioritize local apps
            apps[app.name] = app

        return list(apps.values())

    def load(self, name, parameters=None) -> AppClient:
        try:
            logger.debug('trying to load app %s from filesystem %s', name, self.loader.root)
            return self.loader.load(name, parameters)
        except ValueError:
            logger.debug('Failed to load app %s locally, trying to download...', name)

        if self.repo.exists(name):
            self.repo.download_app(name, self.loader.root)
            app = self.loader.load(name, parameters)
            logger.debug('successfully loaded app %s: %s', name, app)
            return app
        else:
            raise ValueError('No app with name %s found' % name)

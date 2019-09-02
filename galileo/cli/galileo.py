import logging
import os
import shutil
import tempfile

import click
import requests
import yaml

from galileo.apps.repository import validate_manifest


class ApiClient:
    api = 'http://localhost:5001/api'

    def apps_post(self, zip_path):
        with open(zip_path, 'rb') as fd:
            response = requests.post(self._url('/apps'), data=fd.read())
            return response.json()

    def apps_list(self):
        return requests.get(self._url('/apps')).json()

    def _url(self, param):
        return self.api + param


client = ApiClient()


@click.group()
@click.option('--debug/--no-debug', default=False)
def galileo(debug):
    if debug:
        click.echo('Debug mode is %s' % ('on' if debug else 'off'))
        logging.basicConfig(level=logging.DEBUG)


def zipdir(path, zfd):
    # zfd is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            zfd.write(os.path.join(root, file))


@galileo.command()
@click.option('--path', required=True, help='The path to the deployable app')
def deploy_app(path):
    if path.endswith('.zip'):
        app_info = client.apps_post(path)
        click.echo(app_info)
        return 0

    if 'manifest.yml' not in os.listdir(path):
        click.echo(f'No manifest.yml found in {path}')
        return 1

    with open(os.path.join(path, 'manifest.yml'), 'r') as fd:
        y = yaml.safe_load(fd.read())

    manifest = validate_manifest(y)
    click.echo('Manifest OK: %s' % manifest['name'])

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_name = os.path.join(tmpdir, 'app')
        zip_path = os.path.join(tmpdir, 'app.zip')

        # TODO: proper packaging (only what is in the manifest)
        shutil.make_archive(zip_name, 'zip', path)

        app_info = client.apps_post(zip_path)

    click.echo(app_info)


@galileo.command()
def list_apps():
    # TODO: better list command
    apps = client.apps_list()
    for app in apps:
        click.echo(app)


def main(*args, **kwargs):
    global client
    client = ApiClient()
    galileo(*args, **kwargs)


if __name__ == '__main__':
    main()

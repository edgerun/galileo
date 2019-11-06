import json
import logging
import os
import shutil
import tempfile

import click
import requests
import yaml


def validate_manifest(manifest):
    if 'name' not in manifest:
        raise ValueError('No name property found in manifest')

    return manifest


def read_dotfile():
    path = os.path.expanduser('~/.galileo-cli')
    cfg = None

    if os.path.isfile(path):
        with open(path, 'r') as fd:
            cfg = json.load(fd)

    if cfg:
        if 'api' in cfg:
            os.environ['galileo_api_url'] = cfg['api']


class ApiClient:

    def __init__(self, api=None) -> None:
        super().__init__()
        self.api = api or os.getenv('galileo_api_url', 'http://localhost:5001/api')

    def apps_post(self, zip_path):
        with open(zip_path, 'rb') as fd:
            response = requests.post(self._url('/apps'), data=fd.read())
            return response.json()

    def apps_delete(self, app_name):
        return requests.delete(self._url(f'/apps/{app_name}')).json()

    def apps_list(self):
        return requests.get(self._url('/apps')).json()

    def _url(self, param):
        return self.api + param


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


@galileo.group()
def app():
    pass


@app.command('ls', help='List all available galileo apps in the repository')
def app_ls():
    apps = client.apps_list()
    for app in apps:
        click.echo(app)


@app.command('deploy', help='Package and deploy a galileo app to the repository')
@click.option('--path', required=True, help='The path to the deployable app')
def app_deploy(path):
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


@app.command('rm', help='Remove a galileo app')
@click.argument('app-name', type=str, required=True)
def app_rm(app_name):
    response = client.apps_delete(app_name)
    if response:
        click.echo(f'deleted {app_name}')
    else:
        click.echo(f'did not delete {app_name}')


client: ApiClient


def main(*args, **kwargs):
    read_dotfile()

    global client
    client = ApiClient()
    galileo(*args, **kwargs)


if __name__ == '__main__':
    main()

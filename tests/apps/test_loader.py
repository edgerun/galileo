import os
import unittest

from galileo.apps.loader import AppClientLoader, AppClientDirectoryLoader


class AppLoaderTest(unittest.TestCase):
    loader: AppClientLoader

    def setUp(self) -> None:
        repo_dir = os.path.join(os.path.dirname(__file__), 'repo')
        self.loader = AppClientDirectoryLoader(repo_dir)

    def test_list(self):
        apps = self.loader.list()
        self.assertEqual(1, len(apps))
        self.assertEqual('testapp', apps[0].name)

    def test_load_non_existing_app(self):
        self.assertRaises(ValueError, self.loader.load, 'nonexisting')

    def test_load_dir_without_manifest(self):
        self.assertRaises(ValueError, self.loader.load, 'nomanifest')

    def test_load_dir_without_app_name(self):
        self.assertRaises(ValueError, self.loader.load, 'noname')

    def test_load_and_run(self):
        app = self.loader.load('testapp')

        self.assertEqual('testapp', app.name)
        self.assertEqual('galileo.clients.testapp', app.module.__name__)

        request = app.next_request()
        self.assertEqual('testapp', request.app_name)
        self.assertEqual('get', request.method)
        self.assertEqual('/test', request.endpoint)
        self.assertEqual({'counter': 1}, request.kwargs)

        request = app.next_request()
        self.assertEqual('testapp', request.app_name)
        self.assertEqual('get', request.method)
        self.assertEqual('/test', request.endpoint)
        self.assertEqual({'counter': 2}, request.kwargs)


if __name__ == '__main__':
    unittest.main()

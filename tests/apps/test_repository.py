import os
import unittest
import zipfile
from tempfile import TemporaryDirectory

from galileo.apps.repository import Repository

this_dir = os.path.join(os.path.dirname(__file__))


class TemporaryRepositoryResource:
    """
    Prepares a Repository, by zipping all test apps into a temporary directory, and using that directory as root for the
    Repository.
    """
    apps_dir = os.path.join(os.path.dirname(__file__), 'repo')

    tmpdir: TemporaryDirectory
    repository: Repository

    def setUp(self):
        self.tmpdir = TemporaryDirectory(prefix='galileo_unittest_')
        self._prepare_repo()

        self.repository = Repository(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _prepare_repo(self):
        for d in os.listdir(self.apps_dir):

            app_dir = os.path.join(self.apps_dir, d)
            with zipfile.ZipFile(os.path.join(self.tmpdir.name, '%s.zip' % d), 'w') as zipfd:
                for root, dirs, files in os.walk(app_dir):
                    for file in files:
                        zipfd.write(os.path.join(root, file), file)


class RepositoryTest(unittest.TestCase):
    repo = TemporaryRepositoryResource()

    @classmethod
    def setUpClass(cls) -> None:
        cls.repo.setUp()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.repo.tearDown()

    def test_list_archives(self):
        archives = self.repo.repository.list_archives()

        self.assertEqual(3, len(archives), 'expected three archives, got %s' % archives)

        names = [path.split('/')[-1] for path in archives]
        self.assertIn('testapp.zip', names)
        self.assertIn('noname.zip', names)
        self.assertIn('nomanifest.zip', names)

    def test_list_apps(self):
        apps = self.repo.repository.list_apps()
        self.assertEqual(1, len(apps), 'expected one app, got %s' % apps)

        info = apps[0]

        self.assertEqual('testapp', info.name)
        self.assertEqual('testapp', info.manifest['name'])

    def test_get_app(self):
        info = self.repo.repository.get_app('testapp')

        self.assertEqual('testapp', info.name)
        self.assertEqual('testapp', info.manifest['name'])

    def test_get_app_nonexisting_app_returns_none(self):
        info = self.repo.repository.get_app('nonexisting')
        self.assertIsNone(info)

    def test_get_app_invalid_app_returns_none(self):
        info = self.repo.repository.get_app('noname')
        self.assertIsNone(info)

    def test_get_app_without_manifestreturns_none(self):
        info = self.repo.repository.get_app('nomanifest')
        self.assertIsNone(info)

    def test_add_and_get(self):
        repo = self.repo.repository
        info = repo.add(os.path.join(this_dir, 'testapp2.zip'))

        self.assertEqual('testapp2', info.name)
        self.assertEqual({'name': 'testapp2'}, info.manifest)

        actual = repo.get_app('testapp2')
        self.assertEqual(info, actual)

    def test_add_and_remove(self):
        repo = self.repo.repository
        info = repo.add(os.path.join(this_dir, 'testapp2.zip'))

        self.assertTrue(os.path.isfile(info.archive_path))

        deleted = repo.delete_app('testapp2')
        self.assertTrue(deleted)

        self.assertFalse(os.path.isfile(info.archive_path))


if __name__ == '__main__':
    unittest.main()

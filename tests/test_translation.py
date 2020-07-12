import unittest

from galileodb.model import ExperimentConfiguration, WorkloadConfiguration

from galileo.controller import create_instructions


class TestTranslation(unittest.TestCase):
    def test_translation_single_service(self):
        cfg = ExperimentConfiguration(20, 10, [WorkloadConfiguration('aservice', [2, 6], 3, 'constant')])

        commands = create_instructions(cfg, ['h1', 'h2', 'h3'])

        actual = '\n'.join(commands)

        expected = 'spawn h1 aservice 3\n' + \
                   'spawn h2 aservice 3\n' + \
                   'spawn h3 aservice 3\n' + \
                   'rps h1 aservice 1\n' + \
                   'rps h2 aservice 1\n' + \
                   'rps h3 aservice 0\n' + \
                   'sleep 10\n' + \
                   'rps h1 aservice 2\n' + \
                   'rps h2 aservice 2\n' + \
                   'rps h3 aservice 2\n' + \
                   'sleep 10\n' + \
                   'rps h1 aservice 0\n' + \
                   'rps h2 aservice 0\n' + \
                   'rps h3 aservice 0\n' + \
                   'close h1 aservice\n' + \
                   'close h2 aservice\n' + \
                   'close h3 aservice'

        self.assertEqual(expected, actual)

    def test_translation_multiple_services(self):
        cfg = ExperimentConfiguration(20, 10, [WorkloadConfiguration('aservice', [2, 6], 3, 'constant'),
                                               WorkloadConfiguration('bservice', [4, 8], 3, 'constant')])

        commands = create_instructions(cfg, ['h1', 'h2'])

        actual = '\n'.join(commands)

        expected = 'spawn h1 aservice 3\n' + \
                   'spawn h2 aservice 3\n' + \
                   'spawn h1 bservice 3\n' + \
                   'spawn h2 bservice 3\n' + \
                   'rps h1 aservice 1\n' + \
                   'rps h2 aservice 1\n' + \
                   'rps h1 bservice 2\n' + \
                   'rps h2 bservice 2\n' + \
                   'sleep 10\n' + \
                   'rps h1 aservice 3\n' + \
                   'rps h2 aservice 3\n' + \
                   'rps h1 bservice 4\n' + \
                   'rps h2 bservice 4\n' + \
                   'sleep 10\n' + \
                   'rps h1 aservice 0\n' + \
                   'rps h2 aservice 0\n' + \
                   'rps h1 bservice 0\n' + \
                   'rps h2 bservice 0\n' + \
                   'close h1 aservice\n' + \
                   'close h2 aservice\n' + \
                   'close h1 bservice\n' + \
                   'close h2 bservice'

        self.assertEqual(expected, actual)

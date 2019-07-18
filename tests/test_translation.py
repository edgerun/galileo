import unittest

from galileo.controller import create_instructions
from galileo.experiment.model import LoadConfiguration


class TestTranslation(unittest.TestCase):
    def test_translation(self):
        cfg = LoadConfiguration(10, 20, 'aservice', [2, 6], 3)

        commands = iter(create_instructions(cfg, ['h1', 'h2', 'h3']))

        self.assertEqual('spawn h1 aservice 3', next(commands))
        self.assertEqual('spawn h2 aservice 3', next(commands))
        self.assertEqual('spawn h3 aservice 3', next(commands))

        self.assertEqual('rps h1 aservice 1', next(commands))
        self.assertEqual('rps h2 aservice 1', next(commands))
        self.assertEqual('rps h3 aservice 0', next(commands))

        self.assertEqual('sleep 10', next(commands))

        self.assertEqual('rps h1 aservice 2', next(commands))
        self.assertEqual('rps h2 aservice 2', next(commands))
        self.assertEqual('rps h3 aservice 2', next(commands))

        self.assertEqual('sleep 10', next(commands))

        self.assertEqual('rps h1 aservice 0', next(commands))
        self.assertEqual('rps h2 aservice 0', next(commands))
        self.assertEqual('rps h3 aservice 0', next(commands))

        self.assertEqual('close h1 aservice', next(commands))
        self.assertEqual('close h2 aservice', next(commands))
        self.assertEqual('close h3 aservice', next(commands))

        try:
            cmd = next(commands)
            self.fail('there should be more commands, but next returned: %s' % cmd)
        except StopIteration:
            pass

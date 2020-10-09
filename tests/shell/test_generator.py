import unittest

from galileodb.model import ExperimentConfiguration, WorkloadConfiguration

from galileo.shell import generator


class TestGenerator(unittest.TestCase):
    def test_create_instructions_single_service(self):
        cfg = ExperimentConfiguration(20, 10, [WorkloadConfiguration('aservice', [2, 6], 3, 'constant')])

        commands = generator.generate_script(cfg)

        actual = '\n'.join(commands)

        expected = "wl_0 = g.spawn('aservice', 3)\n" + \
                   "wl_0.rps(2/3)\n" + \
                   "sleep(10)\n" + \
                   "wl_0.rps(6/3)\n" + \
                   "sleep(10)\n" + \
                   "wl_0.rps(0)\n" + \
                   "wl_0.close()"

        self.assertEqual(expected, actual)

    def test_translation_multiple_services(self):
        cfg = ExperimentConfiguration(20, 10, [WorkloadConfiguration('aservice', [2, 6], 3, 'constant'),
                                               WorkloadConfiguration('bservice', [4, 8], 2, 'constant')])

        commands = generator.generate_script(cfg)

        actual = '\n'.join(commands)

        expected = "wl_0 = g.spawn('aservice', 3)\n" + \
                   "wl_1 = g.spawn('bservice', 2)\n" + \
                   "wl_0.rps(2/3)\n" + \
                   "wl_1.rps(4/2)\n" + \
                   "sleep(10)\n" + \
                   "wl_0.rps(6/3)\n" + \
                   "wl_1.rps(8/2)\n" + \
                   "sleep(10)\n" + \
                   "wl_0.rps(0)\n" + \
                   "wl_1.rps(0)\n" + \
                   "wl_0.close()\n" + \
                   "wl_1.close()"

        self.assertEqual(expected, actual)

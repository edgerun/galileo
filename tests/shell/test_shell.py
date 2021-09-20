import unittest
from unittest.mock import MagicMock

from galileo.shell.shell import ClientGroup
from galileo.worker.api import ClientDescription


class TestClientGroup(unittest.TestCase):

    def test_add_groups(self):
        ctrl = MagicMock()

        cg1 = ClientGroup(ctrl, [
            ClientDescription('id1', 'worker1', None),
            ClientDescription('id2', 'worker1', None),
            ClientDescription('id3', 'worker2', None),
        ])

        cg2 = ClientGroup(ctrl, [
            ClientDescription('id4', 'worker1', None),
            ClientDescription('id5', 'worker2', None),
            ClientDescription('id6', 'worker2', None),
        ])

        cg3 = cg1 + cg2

        self.assertEqual(6, len(cg3.clients))

        self.assertEqual(cg1.clients[0], cg3.clients[0])
        self.assertEqual(cg2.clients[0], cg3.clients[3])
        self.assertEqual(ctrl, cg1.ctrl)
        self.assertEqual(ctrl, cg2.ctrl)

    def test_add_groups_with_different_ctrl_raises_exception(self):
        ctrl1 = MagicMock()
        ctrl2 = MagicMock()

        cg1 = ClientGroup(ctrl1, [
            ClientDescription('id1', 'worker1', None),
            ClientDescription('id2', 'worker1', None),
            ClientDescription('id3', 'worker2', None),
        ])

        cg2 = ClientGroup(ctrl2, [
            ClientDescription('id4', 'worker1', None),
            ClientDescription('id5', 'worker2', None),
            ClientDescription('id6', 'worker2', None),
        ])

        try:
            _ = cg1 + cg2
            self.fail('expected value error because of differing controllers in client groups')
        except ValueError:
            pass

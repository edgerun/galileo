import unittest

from galileo.util import to_seconds


class TestUtil(unittest.TestCase):
    def test_to_seconds(self):
        self.assertEqual(0, to_seconds(''))
        self.assertEqual(1, to_seconds('1'))
        self.assertEqual(10, to_seconds('10s'))
        self.assertEqual(60, to_seconds('1m'))
        self.assertEqual(600, to_seconds('10m'))
        self.assertEqual(610, to_seconds('10m 10s'))

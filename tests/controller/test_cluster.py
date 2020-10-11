import unittest

from galileo.controller.cluster import pack


class PackTest(unittest.TestCase):
    def test_pack_single(self):
        workers = ['a', 'b', 'c']
        clients = [1, 2, 3]

        result = pack(1, workers, clients)

        expected = {
            'a': 1
        }

        self.assertEqual(expected, result)

    def test_pack_multiple(self):
        workers = ['a', 'b', 'c']
        clients = [5, 2, 1]

        result = pack(5, workers, clients)

        expected = {
            'b': 2,
            'c': 3
        }

        self.assertEqual(expected, result)

    def test_pack_tie(self):
        workers = ['a', 'b', 'c']
        clients = [2, 1, 1]

        result = pack(1, workers, clients)

        expected = {
            'b': 1,
        }

        self.assertEqual(expected, result)

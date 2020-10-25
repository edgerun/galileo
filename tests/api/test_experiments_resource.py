import pymq
from galileodb import Experiment

from galileo.controller import ExperimentController
from tests.api import ResourceTest


class TestExperimentsResource(ResourceTest):

    def test_get_experiments_empty(self):
        result = self.simulate_get('/api/experiments')
        self.assertEqual(result.json, [])

    def test_get_experiments(self):
        self.maxDiff = None
        experiments = [
            Experiment('id1', 'name1', 'creator1', 123, 456, 789, 'FINISH'),
            Experiment('id2', 'name2', 'creator2', 1, 4, 7, 'QUEUED'),
            Experiment('id3', 'name3', 'creator3', 3, 6, 9, 'PROGRESS')
        ]

        self.db_resource.db.save_experiment(experiments[0])
        self.db_resource.db.save_experiment(experiments[1])
        self.db_resource.db.save_experiment(experiments[2])

        result = self.simulate_get('/api/experiments')
        dicts = []
        for exp in experiments:
            dicts.append(exp.__dict__)

        self.assertCountEqual(result.json, dicts)

    def test_post_experiment(self):
        payload = {
            'experiment': {
                'name': 'my_experiment',
                'creator': 'research star'
            },
            'configuration': {
                'duration': '10s',
                'interval': '2s',
                'workloads': [
                    {
                        'service': 'alexnet',
                        'ticks': [1, 2, 3, 1, 1],
                        'arrival_pattern': 'constant',
                        'clients_per_host': 2
                    },
                ]
            }
        }

        self.ctx.cctrl.register_worker('host1')

        result = self.simulate_post('/api/experiments', json=payload)
        self.assertIsNotNone(result.json, 'Response must not be none')

        all_exps = self.db_resource.db.find_all()
        self.assertEqual(len(all_exps), 1)
        exp = all_exps[0]
        self.assertEqual(exp.id, result.json)
        self.assertEqual(exp.status, 'QUEUED')
        self.assertIsNotNone(exp.created)

        load = pymq.queue(ExperimentController.queue_key).get(timeout=2)

        # TODO test workload translation?
        self.assertIsNotNone(load)
        self.assertEqual(exp.id, load.experiment.id)

    # TODO test with no hosts available

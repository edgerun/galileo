from typing import List

from galileodb.model import Experiment, Telemetry, RequestTrace

from tests.api import ResourceTest


class TestExperimentResource(ResourceTest):

    def test_get(self):
        exp = Experiment('id1', 'name1', 'creator1', 123, 456, 789, 'FINISH')
        self.db_resource.db.save_experiment(exp)
        result = self.simulate_get(f'/api/experiments/id1')

        self.assertIsNotNone(result.json)
        self.assertEqual(result.json, exp.__dict__)

    def test_delete(self):
        exp_id = 'id1'
        exp = Experiment(exp_id, 'name1', 'creator1', 1, 20, 7, 'FINISH')
        telemetry: List[Telemetry] = [Telemetry(1, 'metric1', 'node1', 1, exp_id),
                                      Telemetry(2, 'metric2', 'node2', 2, exp_id)]
        traces: List[RequestTrace] = [RequestTrace('req1', 'client1', 'service1', 2, 2, 3),
                                      RequestTrace('req2', 'client2', 'service2', 6, 5, 4)]
        db = self.db_resource.db
        db.save_experiment(exp)
        db.save_telemetry(telemetry)
        db.save_traces(traces)
        db.touch_traces(exp)

        self.simulate_delete('/api/experiments/id1')

        self.assertEqual(len(db.find_all()), 0)

        traces_fetched = db.db.fetchall('SELECT * FROM traces')
        telemetry_fetched = db.db.fetchall('SELECT * FROM telemetry')
        self.assertEqual(len(traces_fetched), 0)
        self.assertEqual(len(telemetry_fetched), 0)
        pass

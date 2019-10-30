import logging
import time

import falcon
import redis
from symmetry.webapp import ApiResource

from galileo.apps.repository import Repository, RepositoryResource
from galileo.controller import ExperimentController, CancelError
from galileo.experiment.db import ExperimentDatabase
from galileo.experiment.experimentd import generate_experiment_id
from galileo.experiment.model import WorkloadConfiguration, ExperimentConfiguration, Experiment
from galileo.experiment.service.experiment import ExperimentService
from galileo.util import to_seconds

logger = logging.getLogger(__name__)


class AppContext:
    rds: redis.Redis
    ectrl: ExperimentController
    exp_db: ExperimentDatabase
    exp_service: ExperimentService
    repository: Repository


def setup(api: falcon.API, context: AppContext):
    api.add_route('/api', ApiResource(api))
    api.add_route('/api/hosts', HostsResource(context.ectrl))
    api.add_route('/api/services', ServicesResource())
    api.add_route('/api/experiments', ExperimentsResource(context.ectrl, context.exp_service))
    api.add_route('/api/experiments/{exp_id}', ExperimentResource(context.exp_service, context.ectrl))

    repo = RepositoryResource(context.repository)
    api.add_route('/api/apps', repo)
    api.add_route('/api/apps/{app_name}', repo, suffix='info')
    api.add_route('/api/apps/{app_name}/download', repo, suffix='download')


class ServicesResource:
    def on_get(self, req, resp):
        # TODO: rethink this
        services = [
            {
                'name': 'mxnet-model-server'
            }
        ]

        resp.media = services


class HostsResource:

    def __init__(self, ectrl: ExperimentController):
        self.ectrl = ectrl

    def on_get(self, req, resp):
        resp.media = list(self.ectrl.list_hosts())


class ExperimentsResource:

    def __init__(self, ectrl: ExperimentController, exp_service: ExperimentService):
        self.ectrl = ectrl
        self.exp_service = exp_service

    def on_get(self, req: falcon.Request, resp):
        logger.debug('fetching all experiments')
        experiments = self.exp_service.find_all()
        logger.debug(f"found {len(experiments)} experiments")
        resp.media = [exp.__dict__ for exp in experiments]

    """
    here's an example request:

    {
        'experiment': { # experiment is optional, all attributes can be generated
            'name': 'my_experiment',
            'creator': 'research star'
        },
        'configuration': {
            'duration': '10s',
            'interval': '2s',
            'workloads': [
                {
                    'service': 'alexnet',
                    'ticks': [1, 2, 3, 1, 1],  # len must be duration / interval
                    'clients_per_host': 2  # optional, will be set to 3 by default,
                    'client_parameters': {"size": "small", "type": "cat"} # optional
                },
                # ...
            ]
        }
    }
    """

    def on_post(self, req: falcon.Request, resp):
        if not self.ectrl.list_hosts():
            raise falcon.HTTPServiceUnavailable('no available hosts to execute the experiment')

        doc = req.media

        exp = doc['experiment'] if 'experiment' in doc else dict()
        if 'id' not in exp:
            exp['id'] = generate_experiment_id()

        exp = Experiment(**exp)
        exp.created = time.time()
        exp.status = 'QUEUED'
        self.exp_service.save(exp)

        logger.debug('deserialized experiment %s', exp)

        workloads = [WorkloadConfiguration(**workload) for workload in doc['configuration']['workloads']]
        duration = to_seconds(doc['configuration']['duration'])
        interval = to_seconds(doc['configuration']['interval'])
        config = ExperimentConfiguration(duration, interval, workloads)
        logger.debug('deserialized experiment config %s', config)
        logger.debug('queuing experiment with id %s', exp.id)
        self.ectrl.queue(config, exp)

        resp.media = exp.id


class ExperimentResource:

    def __init__(self, exp_service: ExperimentService, ectrl: ExperimentController):
        self.exp_service = exp_service
        self.ectrl = ectrl

    def on_get(self, req, resp, exp_id):
        logger.debug('finding experiment %s', exp_id)
        experiment = self.exp_service.find(exp_id)

        if not experiment:
            raise falcon.HTTPNotFound()

        resp.media = experiment.__dict__

    def on_delete(self, req, resp, exp_id):
        logger.debug('deleting experiment %s', exp_id)

        try:
            exp: Experiment = self.exp_service.find(exp_id)
            if exp is None:
                raise falcon.HTTPNotFound()

            if exp.status.lower() == 'queued':
                cancelled = False
                try:
                    cancelled = self.ectrl.cancel(exp_id)
                    self.exp_service.delete(exp_id)
                except CancelError:
                    try:
                        cancelled = self.ectrl.cancel(exp_id)
                        self.exp_service.delete(exp_id)
                    except CancelError:
                        logger.error(f'Cancellation of exp with id {exp_id} failed two times')

                if cancelled:
                    logger.info(f"Experiment {exp_id} was removed from queue")
                else:
                    logger.info(f"Experiment {exp_id} was not removed from queue")
            else:
                self.exp_service.delete(exp_id)
        except ValueError:
            raise falcon.HTTPNotFound()

        resp.media = exp_id


class CORSComponent(object):
    """
    CORS preprocessor from the Falcon documentation.
    """

    def process_response(self, req, resp, resource, req_succeeded):
        resp.set_header('Access-Control-Allow-Origin', '*')

        if (req_succeeded
                and req.method == 'OPTIONS'
                and req.get_header('Access-Control-Request-Method')
        ):
            # NOTE(kgriffs): This is a CORS preflight request. Patch the
            #   response accordingly.

            allow = resp.get_header('Allow')
            resp.delete_header('Allow')

            allow_headers = req.get_header(
                'Access-Control-Request-Headers',
                default='*'
            )

            resp.set_headers((
                ('Access-Control-Allow-Methods', allow),
                ('Access-Control-Allow-Headers', allow_headers),
                ('Access-Control-Max-Age', '86400'),  # 24 hours
            ))

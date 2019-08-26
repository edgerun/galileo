"""
Module to start webapp from WSGI context.


"""
import os

import falcon
import pymq
import redis
from pymq.provider.redis import RedisConfig

from galileo.controller import ExperimentController
from galileo.experiment.db.factory import create_experiment_database_from_env
from galileo.experiment.service.experiment import SimpleExperimentService
from galileo.apps.repository import Repository
from galileo.webapp.app import AppContext, CORSComponent, setup


def create_context() -> AppContext:
    context = AppContext()

    context.rds = redis.Redis(os.getenv('REDIS_HOST', 'localhost'), decode_responses=True)
    pymq.init(RedisConfig(context.rds))

    context.ectrl = ExperimentController(context.rds)
    context.exp_db = create_experiment_database_from_env()
    context.exp_service = SimpleExperimentService(context.exp_db)
    context.repository = Repository('/home/thomas/workspace/mc2/galileo-client-repository')

    return context


api = falcon.API(middleware=[CORSComponent()])
setup(api, create_context())

import unittest.mock

import falcon
import pymq
import redis
from falcon import testing
from galileodb.sql.adapter import ExperimentSQLDatabase
from pymq.provider.redis import RedisConfig

from galileo.controller import ExperimentController, RedisClusterController
from galileo.experiment.service import SimpleExperimentService
from galileo.webapp.app import setup, CORSComponent, AppContext
from tests.testutils import RedisResource, SqliteResource


class ResourceTest(testing.TestCase):
    redis_resource: RedisResource = RedisResource()
    ctx: AppContext

    def setUp(self):
        super(ResourceTest, self).setUp()
        rds = self.init_rds()
        db = self.init_db()
        self.ctx = self.init_context(db, rds)
        self.app = self.create_api(self.ctx)

    def tearDown(self) -> None:
        super(ResourceTest, self).tearDown()
        pymq.shutdown()
        self.redis_resource.tearDown()
        self.db_resource.tearDown()

    def init_db(self):
        self.db_resource = SqliteResource()
        self.db_resource.setUp()
        return self.db_resource.db

    def init_rds(self):
        self.redis_resource.setUp()
        pymq.init(RedisConfig(self.redis_resource.rds))
        return self.redis_resource.rds

    def create_api(self, ctx) -> falcon.API:
        api = falcon.API(middleware=[CORSComponent()])
        setup(api, ctx)
        return api

    @staticmethod
    def init_context(db: ExperimentSQLDatabase, rds: redis.Redis):
        context = AppContext()

        context.rds = rds

        context.cctrl = RedisClusterController(context.rds)
        context.ectrl = ExperimentController(context.rds)
        context.exp_db = db
        context.exp_service = SimpleExperimentService(context.exp_db)
        context.repository = unittest.mock.MagicMock('repository')

        return context

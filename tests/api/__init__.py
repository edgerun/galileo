import falcon
import redis
from falcon import testing
from symmetry import eventbus
from symmetry.eventbus.redis import RedisConfig
from symmetry.webapp import JSONMiddleware

from galileo.controller import ExperimentController
from galileo.experiment.db.sql import ExperimentSQLDatabase
from galileo.experiment.service.experiment import SimpleExperimentService
from galileo.webapp.app import setup, CORSComponent, AppContext
from tests.testutils import RedisResource, SqliteResource


class ResourceTest(testing.TestCase):
    def setUp(self):
        super(ResourceTest, self).setUp()
        rds_resource = self.init_rds()
        db = self.init_db()
        self.app = self.create_api(db, rds_resource)

    def tearDown(self) -> None:
        super(ResourceTest, self).tearDown()
        eventbus.shutdown()
        self.rds_resource.tearDown()
        self.db_resource.tearDown()

    def init_db(self):
        self.db_resource = SqliteResource()
        self.db_resource.setUp()
        return self.db_resource.db

    def init_rds(self):
        self.rds_resource = RedisResource()
        self.rds_resource.setUp()
        rds_resource = self.rds_resource.rds
        return rds_resource

    def create_api(self, db: ExperimentSQLDatabase, rds: redis.Redis) -> falcon.API:
        api = falcon.API(middleware=[CORSComponent(), JSONMiddleware()])
        setup(api, self.init_context(db, rds))
        return api

    @staticmethod
    def init_context(db: ExperimentSQLDatabase, rds: redis.Redis):
        context = AppContext()

        context.rds = rds
        eventbus.init(RedisConfig(context.rds))

        context.ectrl = ExperimentController(context.rds)
        context.exp_db = db
        context.exp_service = SimpleExperimentService(context.exp_db)

        return context

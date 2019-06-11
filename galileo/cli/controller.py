import os

import redis

import symmetry.eventbus as eventbus
from galileo.controller import ExperimentController, ControllerShell
from symmetry.eventbus.redis import RedisConfig


def main():
    rds = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), decode_responses=True)
    eventbus.init(RedisConfig(rds))

    ctrl = ExperimentController(rds)
    ControllerShell(ctrl).run()


if __name__ == '__main__':
    main()

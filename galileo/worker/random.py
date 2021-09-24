import random
import time
import logging
from galileo.worker.context import Context

logger = logging.getLogger(__name__)

class InvalidDistributionException(Exception):
    pass


def constant(x):
    return x


distributions = {
    'constant': constant,
    'uniform': random.uniform,
    'triangular': random.triangular,
    'normalvariate': random.normalvariate,
    'lognormvariate': random.lognormvariate,
    'expovariate': random.expovariate,
    'vonmisesvariate': random.vonmisesvariate,
    'gammavariate': random.gammavariate,
    'gauss': random.gauss,
    'betavariate': random.betavariate,
    'paretovariate': random.paretovariate,
    'weibullvariate': random.weibullvariate
}


def pre_recorded_profile(ctx: Context, list_key: str):
    rds = ctx.create_redis()
    start = time.time()
    values = rds.lrange(list_key, 0, rds.llen(list_key))
    rds.delete(list_key)
    # Values need to be reversed since we originally treated this like a stack
    values.reverse()
    end = time.time()
    logger.debug(f'loaded {len(values)} ia values in {end - start}s from redis')
    for value in values:
        yield float(value)
    logger.info('done')

def create_sampler(distribution: str, args: tuple, ctx: Context, client_id=None):
    """
    Creates a generator for the given distribution with the given arguments.

    :param distribution: the distribution, e.g., 'lognormvariate'
    :param args: the arguments, e.g., (0.5, 1)
    :param ctx: context object
    :return: a generator
    """
    print("create sampler")
    if distribution == 'prerecorded':
        yield from pre_recorded_profile(ctx, client_id)
    else:
        if distribution not in distributions:
            raise InvalidDistributionException('unknown distribution ' + distribution)

        try:
            fn = distributions[distribution]
        except TypeError as e:
            raise InvalidDistributionException('invalid distribution parameters: ' + str(e))

        if args is None:
            args = []

        while True:
            yield fn(*args)

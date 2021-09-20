import random

from galileo.worker.context import Context


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
    print(rds)
    while rds.llen(list_key) != 0:
        ia = float(rds.rpop(list_key))
        print(ia)
        yield ia
    print('done')


def create_sampler(distribution: str, args: tuple, ctx: Context):
    """
    Creates a generator for the given distribution with the given arguments.

    :param distribution: the distribution, e.g., 'lognormvariate'
    :param args: the arguments, e.g., (0.5, 1)
    :param ctx: context object
    :return: a generator
    """
    print("create sampler")
    if distribution == 'prerecorded':
        list_key = args[0]
        yield from pre_recorded_profile(ctx, list_key)
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

import random


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


def create_sampler(distribution: str, args: tuple):
    """
    Creates a generator for the given distribution with the given arguments.

    :param distribution: the distribution, e.g., 'lognormvariate'
    :param args: the arguments, e.g., (0.5, 1)
    :return: a generator
    """
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

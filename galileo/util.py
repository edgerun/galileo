import os
import re
import time
from datetime import timedelta
from inspect import signature
from typing import List
from uuid import uuid4


def read_file(f, mode='rb'):
    """
    Convenience method for reading a file into a byte buffer.
    :param f: path to the file
    :return: a byte array
    """
    with open(f, mode=mode) as reader:
        return reader.read()


def mkdirp(path):
    """
    Creates a directory at the given path with all necessary parent directories. If the path is already a directory,
    nothing happens. If the path is a file, then a FileExistsError will be raised.
    :param path: the desired path
    :return: None
    """
    if not os.path.exists(path):
        os.makedirs(path)

    if os.path.isfile(path):
        raise FileExistsError("%s is an existing file" % path)


def uuid():
    """
    Returns a random UUID as string.

    :return: a UUID
    """
    return str(uuid4())


def namedtuples_from_strings(cls, ls: List[str]):
    params = list(signature(cls).parameters.values())
    tuples = list()
    for v in ls:
        args = v.split(',')
        typed = [params[i].annotation(args[i]) for i in range(len(args))]
        trace = cls(*typed)
        tuples.append(trace)
    return tuples


def subdict(data: dict, keys: list):
    return {k: data[k] for k in keys if k in data}


_time_units = {
    's': 'seconds',
    'm': 'minutes',
    'h': 'hours'
}
_time_pattern = re.compile('([0-9]+)([smh]?)')


def to_seconds(time_str: str) -> int:
    groups = _time_pattern.findall(time_str)

    kwargs = dict()
    for value, unit in groups:
        if not unit:
            unit = 's'
        kwargs[_time_units[unit]] = int(value)

    return round(timedelta(**kwargs).total_seconds())


def poll(condition, timeout=None, interval=0.5):
    remaining = 0
    if timeout is not None:
        remaining = timeout

    while not condition():
        if timeout is not None:
            remaining -= interval

            if remaining <= 0:
                raise TimeoutError('gave up waiting after %s seconds' % timeout)

        time.sleep(interval)

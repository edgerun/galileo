import os
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
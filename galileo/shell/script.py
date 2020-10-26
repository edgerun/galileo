from galileo.shell.shell import sleep

name = 'init'

__all__ = [
    'sleep'
]


def _init(module=None):
    from galileo.worker.context import Context
    from galileo.shell.shell import init_module
    import atexit
    import pymq

    ctx = Context()
    rds = ctx.create_redis()
    init_module(rds, name=module)

    atexit.register(pymq.shutdown)


_init('__main__')

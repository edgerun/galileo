import argparse

from galileo.shell.shell import *


def _init():
    import redis

    rds = redis.Redis(
        host=os.getenv('galileo_redis_host', 'localhost'),
        port=int(os.getenv('galileo_redis_port', 6379)),
        decode_responses=True
    )
    init_module(rds, __name__)


def _init_standalone():
    from tempfile import mktemp
    from threading import Thread
    from shutil import rmtree
    from galileo.worker.context import Context
    from galileo.worker.daemon import WorkerDaemon

    ctx = Context()

    # prepare embedded redis instance
    filename = mktemp(prefix='galileo_shell_', suffix='.db')
    os.environ['galileo_redis_host'] = 'file://' + filename  # Context resolves this correctly using redislite
    rds = ctx.create_redis()
    rds.randomkey()

    # init this module with global variables
    init_module(rds, __name__)

    # start worker daemon
    global eventbus
    daemon = WorkerDaemon(ctx=ctx, eventbus=eventbus)
    t_daemon = Thread(target=daemon.run, daemon=True)
    t_daemon.start()

    # register cleanup method
    def cleanup():
        daemon.close()
        eventbus.close()

        # remove redislite db
        rds.shutdown()
        os.remove(filename)
        os.remove(rds.redis_configuration_filename)
        os.remove(rds.settingregistryfile)
        rmtree(rds.redis_dir)

    atexit.register(cleanup)


def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--standalone', required=False, action="store_true",
                        help='also start an embedded redis server and a worker instance')
    args = parser.parse_args()

    if args.standalone:
        print('running in standalone mode')
        _init_standalone()
    else:
        _init()

    if is_interactive:
        sys.ps1 = prompt

        print(banner)
        print('Welcome to the galileo shell!')
        print('')
        print('Type `usage` to list available functions')
        print('')
    else:
        sys.ps1 = ''


if __name__ == '__main__':
    # python -i shell.py will execute to here and then drop into the interactive shell
    _main()

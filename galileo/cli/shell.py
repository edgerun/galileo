import argparse

import redis

from galileo.shell.shell import *


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=False, type=argparse.FileType('r'),
                        help='read and execute the given file instead of running in interactive mode')
    args = parser.parse_args()

    rds = redis.Redis(
        host=os.getenv('galileo_redis_host', 'localhost'),
        port=int(os.getenv('galileo_redis_port', 6379)),
        decode_responses=True
    )
    init_module(rds, __name__)

    if args.source:
        exec(args.source.read(), globals())
        exit(0)

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
    main()

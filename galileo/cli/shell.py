import redis

from galileo.shell.shell import *


def main():
    rds = redis.Redis(
        host=os.getenv('galileo_redis_host', 'localhost'),
        port=int(os.getenv('galileo_redis_port', 6379)),
        decode_responses=True
    )
    init_module(rds, __name__)

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

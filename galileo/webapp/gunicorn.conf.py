import logging


def on_starting(server):
    # simple way of getting the logs to output by reusing gunicorn's --log-level config
    logging.basicConfig(level=logging.getLogger('gunicorn.error').level)


def on_exit(server):
    pass

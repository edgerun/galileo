import logging
import signal
import time
from multiprocessing import Queue
from queue import Full

import requests

from galileo.experiment.model import ServiceRequestTrace
from galileo.worker.context import Context

POISON = "__POISON__"

logger = logging.getLogger(__name__)


class Client:
    def __init__(self, client_id: str, ctx: Context, request_queue: Queue, trace_queue: Queue) -> None:
        super().__init__()
        self.router = ctx.create_router()
        self.client_id = client_id
        self.q = request_queue
        self.traces = trace_queue

    def run(self):
        client_id = self.client_id
        q = self.q
        traces = self.traces
        router = self.router

        try:
            while True:
                logger.debug("client %s waiting for next request", client_id)
                request = q.get()
                if request == POISON:
                    break

                logger.debug('client %s processing request %s', client_id, request)
                request.client_id = client_id

                try:
                    response: requests.Response = router.request(request)
                    host = response.url.split("//")[-1].split("/")[0].split('?')[0]
                    t = ServiceRequestTrace(client_id, request.service, host, request.created, request.sent,
                                            time.time())
                except Exception as e:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.exception('error while handling request %s', request)
                    else:
                        logger.error('error while handling request %sL %s', request, e)

                    t = ServiceRequestTrace(client_id, request.service, 'none', request.created, -1, time.time())

                try:
                    traces.put_nowait(t)
                except Full:
                    pass

        except:
            logger.exception("Error during read loop in client %s", client_id)

    def __str__(self):
        return 'Client{client_id=%s}' % self.client_id


def run(client_id: str, ctx: Context, request_queue: Queue, trace_queue: Queue):
    client = Client(client_id, ctx, request_queue, trace_queue)

    def sigterm(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, sigterm)

    try:
        logger.info("%s starting", client)
        client.run()
    except KeyboardInterrupt:
        pass

    logger.info("%s exitting", client)

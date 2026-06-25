#!/usr/bin/env python3
import os
import sys

# Ensure the project root is on sys.path so shared/ and jobs/ are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import redis
from rq import Queue, Worker

from shared.logging import setup_logging, get_logger
from shared.settings import settings

setup_logging("worker")
log = get_logger("worker")

settings.validate_required()

QUEUE_NAME = settings.rq_queue
REDIS_HOST = settings.redis_host
REDIS_PORT = settings.redis_port


def main():
    conn = redis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
    q = Queue(QUEUE_NAME, connection=conn)
    w = Worker([q], connection=conn)
    log.info("worker_started", queue=QUEUE_NAME)
    w.work(with_scheduler=False)


if __name__ == "__main__":
    main()

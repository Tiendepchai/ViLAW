#!/usr/bin/env python3
import os
import redis
from rq import Queue, Worker

# Tên queue lấy từ ENV (trùng với ingestor)
QUEUE_NAME = os.getenv("RQ_QUEUE", "bo_pd_jobs")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

def main():
    # Kết nối Redis
    conn = redis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}/0")

    # Tạo queue & worker gắn kết nối
    q = Queue(QUEUE_NAME, connection=conn)
    w = Worker([q], connection=conn)

    # Bắt đầu chạy worker (blocking)
    w.work(with_scheduler=False)

if __name__ == "__main__":
    main()


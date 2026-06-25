import os

import redis
from fastapi import FastAPI
from rq import Queue

app = FastAPI()

r = redis.from_url(
    f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}/0"
)
q = Queue(os.getenv("RQ_QUEUE", "bo_pd_jobs"), connection=r)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/ingest/refresh")
def refresh():
    job = q.enqueue_call(
        func="jobs.pipeline.refresh_pipeline",
        args=(),
        kwargs={},
        result_ttl=24 * 3600,
        timeout=60 * 60 * 2,
    )
    return {"enqueued": True, "job_id": job.id}

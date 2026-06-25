import os

import redis
from fastapi import FastAPI
from rq import Queue

from shared.logging import setup_logging, get_logger
from shared.settings import settings
from shared.db import configure as db_configure, migrate as db_migrate

setup_logging("ingestor")
log = get_logger("ingestor")

settings.validate_required()
db_configure()
db_migrate()

app = FastAPI(title="ViLAW Ingestor", version="1.0.0")

r = redis.from_url(
    f"redis://{settings.redis_host}:{settings.redis_port}/0"
)
q = Queue(settings.rq_queue, connection=r)


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
    log.info("refresh_enqueued", job_id=job.id)
    return {"enqueued": True, "job_id": job.id}


@app.on_event("shutdown")
def shutdown():
    log.info("shutdown", service="ingestor")

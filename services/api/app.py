import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from search import Searcher
from rag import run_rag
from stream import router as stream_router
from shared.logging import setup_logging, get_logger
from shared.settings import settings
from shared.db import configure as db_configure, migrate as db_migrate

setup_logging("api")
log = get_logger("api")

settings.validate_required()
db_configure()
db_migrate()

app = FastAPI(
    title="ViLAW API",
    version="1.0.0",
    description="Vietnamese Legal RAG — Bộ Pháp Điển search & QA",
    contact={"name": "ViLAW"},
)

INDEX_DIR = settings.index_dir

_searcher = None
def get_searcher():
    global _searcher
    if _searcher is None:
        _searcher = Searcher(INDEX_DIR)
    return _searcher

class Q(BaseModel):
    q: str
    top_k: int = 6

# ── Error middleware ──
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": exc.status_code},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    log.error("unhandled_error", path=str(request.url), error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "code": 500},
    )

# ── Routes ──
app.include_router(stream_router)

@app.get("/health")
def health():
    ready = os.path.exists(os.path.join(INDEX_DIR, "bo_pd.index"))
    return {"status": "ok", "index_dir": INDEX_DIR, "index_ready": ready}

@app.post("/v1/search")
def search(body: Q):
    s = get_searcher()
    log.info("search", q=body.q, top_k=body.top_k)
    return {"query": body.q, "hits": s.search(body.q, body.top_k)}

@app.post("/v1/ask")
def ask(body: Q):
    s = get_searcher()
    try:
        hits = s.search(body.q, max(body.top_k, 10))
    except AssertionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    log.info("ask", q=body.q, top_k=body.top_k)
    out = run_rag(body.q, hits, body.top_k)
    return {"query": body.q, **out}

# ── Graceful shutdown ──
@app.on_event("shutdown")
def shutdown():
    log.info("shutdown", service="api")


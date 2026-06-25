import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

from search import Searcher
from rag import run_rag
from stream import router as stream_router
from feedback import router as feedback_router
from auth import auth_middleware
from metrics import instrumentator
from shared.logging import setup_logging, get_logger
from shared.settings import settings
from shared.db import configure as db_configure, migrate as db_migrate

setup_logging("api")
log = get_logger("api")

settings.validate_required()
db_configure()
db_migrate()

# ── Rate limiter ──
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="ViLAW API",
    version="1.0.0",
    description="Vietnamese Legal RAG — Bộ Pháp Điển search & QA",
    contact={"name": "ViLAW"},
    docs_url="/docs",
    redoc_url="/redoc",
)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# ── Auth middleware ──
app.middleware("http")(auth_middleware)

# ── Metrics ──
if os.getenv("ENABLE_METRICS", "").lower() in ("1", "true"):
    instrumentator.instrument(app).expose(app)

INDEX_DIR = settings.index_dir

_searcher = None
def get_searcher():
    global _searcher
    if _searcher is None:
        _searcher = Searcher(INDEX_DIR)
    return _searcher

class Q(BaseModel):
    q: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=6, ge=1, le=20)

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
app.include_router(feedback_router)

@app.get("/health")
def health():
    ready = os.path.exists(os.path.join(INDEX_DIR, "bo_pd.index"))
    return {
        "status": "ok",
        "version": "1.0.0",
        "index_dir": INDEX_DIR,
        "index_ready": ready,
        "auth_enabled": settings.auth_enabled,
    }

@app.post("/v1/search")
@limiter.limit("60/minute")
def search(body: Q, request: Request):
    s = get_searcher()
    log.info("search", q=body.q, top_k=body.top_k)
    return {"query": body.q, "hits": s.search(body.q, body.top_k)}

@app.post("/v1/ask")
@limiter.limit("10/minute")
def ask(body: Q, request: Request):
    s = get_searcher()
    try:
        hits = s.search(body.q, max(body.top_k, 10))
    except AssertionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    log.info("ask", q=body.q, top_k=body.top_k)
    out = run_rag(body.q, hits, body.top_k)
    return {"query": body.q, **out}

# Auth login endpoint (when AUTH_ENABLED=true)
@app.post("/v1/auth/login")
def login():
    from auth import create_token
    token = create_token()
    return {"token": token, "token_type": "bearer"}

# ── Graceful shutdown ──
@app.on_event("shutdown")
def shutdown():
    log.info("shutdown", service="api")

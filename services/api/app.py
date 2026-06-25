# services/api/app.py
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from search import Searcher
from rag import run_rag

app = FastAPI()
INDEX_DIR = os.getenv("INDEX_DIR", "/app/indexes")

_searcher = None
def get_searcher():
    global _searcher
    if _searcher is None:
        _searcher = Searcher(INDEX_DIR)
    return _searcher

class Q(BaseModel):
    q: str
    top_k: int = 6

@app.get("/health")
def health():
    ready = os.path.exists(os.path.join(INDEX_DIR, "bo_pd.index"))
    return {"status": "ok", "index_dir": INDEX_DIR, "index_ready": ready}

@app.post("/search")
def search(body: Q):
    s = get_searcher()
    return {"query": body.q, "hits": s.search(body.q, body.top_k)}

@app.post("/ask")
def ask(body: Q):
    s = get_searcher()
    try:
        hits = s.search(body.q, max(body.top_k, 10))  # lấy dư để rerank
    except AssertionError as e:
        # lỗi lệch dim sẽ ném exception từ Searcher.__init__
        raise HTTPException(status_code=503, detail=str(e))
    out = run_rag(body.q, hits, body.top_k)
    return {"query": body.q, **out}


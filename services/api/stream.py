"""SSE streaming endpoint for RAG answers.

Usage:
  POST /v1/ask/stream  {"q": "...", "top_k": 6}
  → text/event-stream with token-by-token LLM output
  → final event with citations
"""

import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from shared.logging import get_logger
from shared.settings import settings
from rag import pack_contexts, build_prompt, generate_answer_stream
from search import Searcher

log = get_logger("stream")
router = APIRouter()

INDEX_DIR = settings.index_dir

_searcher = None


def get_searcher():
    global _searcher
    if _searcher is None:
        _searcher = Searcher(INDEX_DIR)
    return _searcher


class StreamQ(BaseModel):
    q: str
    top_k: int = 6


async def _generate_events(prompt: str) -> AsyncGenerator[str, None]:
    for token in generate_answer_stream(prompt):
        yield f"data: {json.dumps({'token': token})}\n\n"


@router.post("/v1/ask/stream")
async def ask_stream(body: StreamQ, request: Request):
    if not body.q.strip():
        raise HTTPException(status_code=400, detail="Missing query")

    s = get_searcher()
    try:
        hits = s.search(body.q, max(body.top_k * 2, 10))
    except AssertionError as e:
        raise HTTPException(status_code=503, detail=str(e))

    kept = pack_contexts(hits, max_chars=settings.rag_max_chars)

    if not kept:
        async def no_context():
            yield f"data: {json.dumps({'token': 'Không tìm thấy trích dẫn phù hợp.'})}\n\n"
            yield f"data: {json.dumps({'citations': [], 'done': True})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            no_context(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    prompt = build_prompt(body.q, kept)

    cites = [
        {"tag": f"C{i+1}", "title": c["title"], "url": c.get("url"), "doc_id": c["id"], "chunk_id": c.get("chunk_id")}
        for i, c in enumerate(kept)
    ]

    async def generate():
        async for event in _generate_events(prompt):
            yield event
            if await request.is_disconnected():
                break
        yield f"data: {json.dumps({'citations': cites, 'done': True})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )

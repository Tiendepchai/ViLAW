"""SSE streaming endpoint for RAG answers.

Usage:
  POST /v1/ask/stream  {"q": "...", "top_k": 6}
  → text/event-stream with token-by-token LLM output
  → final event with citations
"""

import json
import os
from typing import AsyncGenerator

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from shared.logging import get_logger
from shared.settings import settings
from rag import pack_contexts, build_prompt
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


async def _stream_ollama(prompt: str) -> AsyncGenerator[str, None]:
    """Yield SSE data events from Ollama streaming."""
    host = settings.ollama_host
    model = settings.rag_model

    try:
        r = requests.post(
            f"{host}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": True,
                "options": {"temperature": 0.1},
            },
            stream=True,
            timeout=600,
        )
        r.raise_for_status()
    except Exception as e:
        log.error("ollama_stream_start_failed", error=str(e))
        yield f"data: {json.dumps({'error': 'Không thể kết nối mô hình ngôn ngữ.'})}\n\n"
        yield "data: [DONE]\n\n"
        return

    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            chunk = json.loads(line)
            token = chunk.get("response", "")
            if token:
                yield f"data: {json.dumps({'token': token})}\n\n"
            if chunk.get("done"):
                break
        except json.JSONDecodeError:
            continue


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
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    prompt = build_prompt(body.q, kept)

    # Build citations before streaming
    cites = [
        {
            "tag": f"C{i+1}",
            "title": c["title"],
            "url": c.get("url"),
            "doc_id": c["id"],
            "chunk_id": c.get("chunk_id"),
        }
        for i, c in enumerate(kept)
    ]

    async def generate():
        async for event in _stream_ollama(prompt):
            yield event
            if await request.is_disconnected():
                break
        # Final citations event
        yield f"data: {json.dumps({'citations': cites, 'done': True})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

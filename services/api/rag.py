import os, re
import json
from typing import List, Dict, Any
import requests

from shared.logging import get_logger
from shared.settings import settings

log = get_logger("rag")

RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.35"))


def pack_contexts(hits: List[Dict[str, Any]], max_chars: int = 8000) -> List[Dict[str, Any]]:
    filtered = [h for h in hits if h.get("score", 0) >= RELEVANCE_THRESHOLD]
    dropped = len(hits) - len(filtered)
    if dropped:
        log.info("relevance_filter", kept=len(filtered), dropped=dropped, threshold=RELEVANCE_THRESHOLD)
    if not filtered:
        return []

    best_per_doc: Dict[str, dict] = {}
    for h in filtered:
        m = h.get("meta", {})
        did = m.get("doc_id") or m.get("id") or ""
        if did not in best_per_doc or h["score"] > best_per_doc[did]["score"]:
            best_per_doc[did] = h

    deduped = sorted(best_per_doc.values(), key=lambda x: x["score"], reverse=True)
    seen_urls: set[str] = set()
    kept, total = [], 0
    for h in deduped:
        m = h.get("meta", {})
        text = (m.get("text") or m.get("noi_dung") or "").strip()
        if not text:
            continue
        url = m.get("url") or ""
        need = len(text) + 200
        if total + need > max_chars:
            break
        kept.append({
            "id": m.get("doc_id") or m.get("id") or "",
            "title": m.get("tieu_de_dieu") or m.get("title") or m.get("so_dieu") or "Trích dẫn",
            "url": url,
            "chunk_id": m.get("chunk_id"),
            "section": m.get("section", ""),
            "text": text,
        })
        if url:
            seen_urls.add(url)
        total += need
    return kept


def build_prompt(question: str, contexts: List[Dict[str, Any]]) -> str:
    header = (
        "Bạn là trợ lý pháp lý tiếng Việt. Chỉ dùng thông tin trong các trích dẫn dưới đây. "
        "Nếu thiếu căn cứ, hãy trả lời: 'Không đủ căn cứ trong trích dẫn'. "
        "Luôn có mục 'Nguồn' liệt kê [C1], [C2] theo thứ tự Context.\n\n"
        "Yêu cầu:\n"
        "- Trích dẫn chính xác số điều, khoản khi có thể.\n"
        "- Trả lời ngắn gọn (3-7 câu).\n"
        "- Không bịa thông tin ngoài trích dẫn.\n"
        "- Nếu câu hỏi không liên quan đến pháp luật, hãy nói 'Tôi chỉ hỗ trợ tra cứu pháp luật.'\n"
    )
    ctx_lines = []
    for i, c in enumerate(contexts, 1):
        section_info = f" [{c['section']}]" if c.get("section") else ""
        head = f"[C{i}] {c['title']}{section_info}" + (f" ({c['url']})" if c.get("url") else "")
        ctx_lines.append(head + "\n" + c["text"])
    ctx_block = "\n\n".join(ctx_lines)
    instr = f"\n---\nQuestion: {question}\nTrả lời ngắn gọn (3–7 câu), chính xác, có mục 'Nguồn'. Không bịa.\n"
    return header + "\n== Context ==\n" + ctx_block + instr


# ── LLM backends ──

def _call_ollama(prompt: str) -> str:
    host = settings.ollama_host
    model = settings.rag_model
    try:
        r = requests.post(
            f"{host}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.1}},
            timeout=600,
        )
        r.raise_for_status()
        return (r.json().get("response") or "").strip()
    except Exception as e:
        log.error("ollama_call_failed", error=str(e))
        return "Lỗi khi gọi mô hình ngôn ngữ."


def _call_openai(prompt: str) -> str:
    """Call OpenAI-compatible chat completions API."""
    base = settings.openai_base_url.rstrip("/")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.openai_api_key}",
    }
    body = {
        "model": settings.openai_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    try:
        r = requests.post(f"{base}/chat/completions", json=body, headers=headers, timeout=600)
        r.raise_for_status()
        return (r.json()["choices"][0]["message"]["content"] or "").strip()
    except Exception as e:
        log.error("openai_call_failed", error=str(e))
        return "Lỗi khi gọi mô hình ngôn ngữ."


def _summary_only(prompt: str) -> str:
    refs = ", ".join(re.findall(r"\[C\d+\]", prompt))
    return "Không có LLM. Trích dẫn dùng: " + refs


def generate_answer(prompt: str) -> str:
    if settings.openai_base_url and settings.openai_api_key:
        return _call_openai(prompt)
    backend = os.getenv("RAG_BACKEND", "ollama").lower()
    if backend == "ollama":
        return _call_ollama(prompt)
    return _summary_only(prompt)


def generate_answer_stream(prompt: str):
    """Generator yielding token strings. Chooses backend automatically."""
    if settings.openai_base_url and settings.openai_api_key:
        yield from _stream_openai(prompt)
    else:
        yield from _stream_ollama(prompt)


def _stream_ollama(prompt: str):
    host = settings.ollama_host
    model = settings.rag_model
    try:
        r = requests.post(
            f"{host}/api/generate",
            json={"model": model, "prompt": prompt, "stream": True, "options": {"temperature": 0.1}},
            stream=True,
            timeout=600,
        )
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                chunk = json.loads(line)
                token = chunk.get("response", "")
                if token:
                    yield token
                if chunk.get("done"):
                    break
            except json.JSONDecodeError:
                continue
    except Exception as e:
        log.error("ollama_stream_failed", error=str(e))
        yield "[Lỗi kết nối model]"


def _stream_openai(prompt: str):
    base = settings.openai_base_url.rstrip("/")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.openai_api_key}",
    }
    body = {
        "model": settings.openai_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "stream": True,
    }
    try:
        r = requests.post(f"{base}/chat/completions", json=body, headers=headers, stream=True, timeout=600)
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data = line[6:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    yield token
            except json.JSONDecodeError:
                continue
    except Exception as e:
        log.error("openai_stream_failed", error=str(e))
        yield "[Lỗi kết nối model]"


def run_rag(question: str, hits: List[Dict[str, Any]], top_k: int) -> Dict[str, Any]:
    kept = pack_contexts(hits[: max(top_k, 10)], max_chars=settings.rag_max_chars)
    if not kept:
        return {"answer": "Không tìm thấy trích dẫn phù hợp.", "citations": [], "used_ctx": 0}
    prompt = build_prompt(question, kept)
    answer = generate_answer(prompt)
    cites = [
        {"tag": f"C{i+1}", "title": c["title"], "url": c.get("url"), "doc_id": c["id"], "chunk_id": c.get("chunk_id")}
        for i, c in enumerate(kept)
    ]
    log.info("rag_done", used_ctx=len(kept), answer_len=len(answer))
    return {"answer": answer, "citations": cites, "used_ctx": len(kept)}

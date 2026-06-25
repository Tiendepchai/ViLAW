# services/api/rag.py
import os, re
from typing import List, Dict, Any
import requests

def pack_contexts(hits: List[Dict[str, Any]], max_chars: int = 8000) -> List[Dict[str, Any]]:
    seen, kept, total = set(), [], 0
    for h in hits:  # giữ đúng thứ tự similarity từ FAISS
        m = h["meta"]
        did = m.get("doc_id") or m.get("id") or ""
        if did in seen:
            continue
        text = (m.get("text") or m.get("noi_dung") or "").strip()
        if not text:
            continue
        need = len(text) + 200
        if total + need > max_chars:
            break
        kept.append({
            "id": did,
            "title": m.get("title") or m.get("tieu_de") or "Trích dẫn",
            "url": m.get("url"),
            "chunk_id": m.get("chunk_id"),
            "text": text
        })
        seen.add(did); total += need
    return kept

def build_prompt(question: str, contexts: List[Dict[str, Any]]) -> str:
    header = (
        "Bạn là trợ lý pháp lý tiếng Việt. Chỉ dùng thông tin trong các trích dẫn dưới đây. "
        "Nếu thiếu căn cứ, hãy trả lời: 'Không đủ căn cứ trong trích dẫn'. "
        "Luôn có mục 'Nguồn' liệt kê [C1], [C2] theo thứ tự Context.\n"
    )
    ctx_lines = []
    for i, c in enumerate(contexts, 1):
        head = f"[C{i}] {c['title']}" + (f" ({c['url']})" if c.get("url") else "")
        ctx_lines.append(head + "\n" + c["text"])
    ctx_block = "\n\n".join(ctx_lines)
    instr = f"\n---\nQuestion: {question}\nTrả lời ngắn gọn (3–7 câu), chính xác, có mục 'Nguồn'. Không bịa.\n"
    return header + "\n== Context ==\n" + ctx_block + instr

def _call_ollama(prompt: str) -> str:
    host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
    model = os.getenv("RAG_MODEL", "qwen2.5:7b")
    r = requests.post(f"{host}/api/generate",
                      json={"model": model, "prompt": prompt, "stream": False,
                            "options": {"temperature": 0.1}},
                      timeout=600)
    r.raise_for_status()
    return (r.json().get("response") or "").strip()

def _summary_only(prompt: str) -> str:
    refs = ", ".join(re.findall(r"\[C\d+\]", prompt))
    return "Không có LLM. Trích dẫn dùng: " + refs

def generate_answer(prompt: str) -> str:
    backend = os.getenv("RAG_BACKEND", "ollama").lower()  # 'ollama' | 'summary'
    return _call_ollama(prompt) if backend == "ollama" else _summary_only(prompt)

def run_rag(question: str, hits: List[Dict[str, Any]], top_k: int) -> Dict[str, Any]:
    kept = pack_contexts(hits[:max(top_k, 5)],
                         max_chars=int(os.getenv("RAG_MAX_CHARS", "8000")))
    prompt = build_prompt(question, kept)
    answer = generate_answer(prompt)
    cites = [{"tag": f"C{i+1}", "title": c["title"], "url": c.get("url"),
              "doc_id": c["id"], "chunk_id": c.get("chunk_id")} for i, c in enumerate(kept)]
    return {"answer": answer, "citations": cites, "used_ctx": len(kept)}


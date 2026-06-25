"""Section-aware chunking for Vietnamese legal documents.

Chunks at 'điều' (article) boundaries, then splits long articles
by paragraph groups — never splits inside a sentence.
"""

import re

# Pattern to detect article headers: "Điều 24.9.NĐ.1.", "Điều 1.", etc.
_ARTICLE_RE = re.compile(r'^(Điều\s+[\d\w.]+\.)', re.IGNORECASE)

# Max chars per chunk (soft — won't break mid-article)
_MAX_CHARS = 1500


def _parse_sections(text: str) -> list[dict]:
    """Split text into sections at article boundaries.

    Returns [{"header": "Điều 1.", "body": "..."}, ...]
    """
    lines = text.split("\n")
    sections = []
    current: list[str] = []
    current_header = "Mở đầu"

    for line in lines:
        m = _ARTICLE_RE.match(line.strip())
        if m:
            if current:
                sections.append({"header": current_header, "body": "\n".join(current).strip()})
            current_header = m.group(1).strip()
            current = [line]
        else:
            current.append(line)

    if current:
        sections.append({"header": current_header, "body": "\n".join(current).strip()})

    return sections


def _split_long_body(body: str, max_len: int, overlap_lines: int = 3) -> list[str]:
    """Split a single article body by paragraph groups if over max_len."""
    paras = [p for p in body.split("\n") if p.strip()]
    if not paras:
        return [body] if body.strip() else []

    if len(body) <= max_len:
        return [body]

    chunks = []
    start = 0
    while start < len(paras):
        end = start + 1
        length = len(paras[start])
        while end < len(paras) and length + len(paras[end]) + 1 <= max_len:
            length += len(paras[end]) + 1
            end += 1
        chunks.append("\n".join(paras[start:end]))
        # overlap: rewind by overlap_lines but at least 1 forward
        start = max(end - overlap_lines, start + 1)

    return chunks


def chunk_document(
    doc_id: str,
    text: str,
    meta: dict | None = None,
    max_chars: int = _MAX_CHARS,
) -> list[dict]:
    """Chunk a legal document into semantically meaningful pieces.

    Returns list of {"id": chunk_id, "text": ..., "meta": ...}
    where chunk_id encodes document hierarchy.
    """
    meta = meta or {}
    sections = _parse_sections(text)
    chunks = []

    for sec in sections:
        leader = sec["header"]
        bodies = _split_long_body(sec["body"], max_chars)
        if not bodies:
            continue
        for i, body in enumerate(bodies, 1):
            chunk_text = f"{leader}\n{body}" if leader else body
            chunk_id = f"{doc_id}#s{i}"
            chunk_meta = {
                **meta,
                "doc_id": doc_id,
                "section": leader,
                "chunk_id": chunk_id,
                "chunk_index": i,
            }
            chunks.append({"id": chunk_id, "text": chunk_text.strip(), "meta": chunk_meta})

    return chunks

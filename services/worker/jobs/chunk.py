import hashlib
from shared.db import get_all_document_ids, get_chunks_by_doc_id, delete_chunks_by_doc_id, insert_chunks, get_conn
from shared.logging import get_logger

log = get_logger("chunk")


def to_chunks(text, max_len=1100, overlap=150):
    parts, cur = [], []
    length = 0
    for line in text.split("\n"):
        if length + len(line) + 1 > max_len and cur:
            parts.append("\n".join(cur))
            while cur and sum(len(x) + 1 for x in cur) > overlap:
                length -= len(cur[0]) + 1
                cur = cur[1:]
        cur.append(line)
        length += len(line) + 1
    if cur:
        parts.append("\n".join(cur))
    return parts


def hash_chunk(doc_id: str, idx: int, text: str) -> str:
    return hashlib.sha256(f"{doc_id}#c{idx}:{text}".encode()).hexdigest()[:16]


def run():
    doc_ids = get_all_document_ids()
    total_chunks = 0

    for doc_id in doc_ids:
        # Get existing chunks for this doc
        existing = get_chunks_by_doc_id(doc_id)
        existing_hashes = {c["chunk_hash"] for c in existing}

        # Fetch full doc text from DB
        from shared.db import get_conn

        with get_conn() as conn:
            row = conn.execute(
                "SELECT id, noi_dung, chu_de, de_muc, so_dieu, tieu_de_dieu, nguon, path_goc FROM documents WHERE id=?",
                (doc_id,),
            ).fetchone()

        if not row:
            continue
        doc = dict(row)
        text = doc.get("noi_dung", "") or ""
        if not text.strip():
            continue

        new_chunks_for_doc = []
        chunk_texts = to_chunks(text)
        for i, chunk_text in enumerate(chunk_texts):
            h = hash_chunk(doc_id, i, chunk_text)
            if h in existing_hashes:
                continue  # unchanged chunk, skip
            new_chunks_for_doc.append(
                {
                    "doc_id": doc_id,
                    "chunk_index": i + 1,
                    "text": chunk_text,
                    "chunk_hash": h,
                }
            )

        if new_chunks_for_doc:
            # Remove old chunks for this doc, insert new ones
            delete_chunks_by_doc_id(doc_id)
            insert_chunks(new_chunks_for_doc)
            total_chunks += len(new_chunks_for_doc)

    log.info("chunk_done", total_chunks=total_chunks, docs_processed=len(doc_ids))
    return {"chunks": total_chunks}

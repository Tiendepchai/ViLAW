import hashlib
from shared.db import get_all_document_ids, get_chunks_by_doc_id, delete_chunks_by_doc_id, insert_chunks, get_conn
from shared.semantic_chunker import chunk_document
from shared.logging import get_logger

log = get_logger("chunk")


def hash_chunk(doc_id: str, chunk: dict) -> str:
    return hashlib.sha256(f"{doc_id}:{chunk['text']}".encode()).hexdigest()[:16]


def run():
    doc_ids = get_all_document_ids()
    total_chunks = 0

    for doc_id in doc_ids:
        existing = get_chunks_by_doc_id(doc_id)
        existing_hashes = {c["chunk_hash"] for c in existing}

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

        meta = {
            "chu_de": doc.get("chu_de", ""),
            "de_muc": doc.get("de_muc", ""),
            "so_dieu": doc.get("so_dieu", ""),
            "tieu_de_dieu": doc.get("tieu_de_dieu", ""),
            "nguon": doc.get("nguon", ""),
        }

        semantic_chunks = chunk_document(doc_id, text, meta)
        new_chunks = []
        for c in semantic_chunks:
            h = hash_chunk(doc_id, c)
            if h in existing_hashes:
                continue
            new_chunks.append(
                {
                    "doc_id": doc_id,
                    "chunk_index": c["meta"]["chunk_index"],
                    "text": c["text"],
                    "chunk_hash": h,
                }
            )

        if new_chunks:
            delete_chunks_by_doc_id(doc_id)
            insert_chunks(new_chunks)
            total_chunks += len(new_chunks)

    log.info("semantic_chunk_done", total_chunks=total_chunks, docs_processed=len(doc_ids))
    return {"chunks": total_chunks}

import os
import numpy as np
from shared.embedding import get_embedder
from shared.faiss_io import build_index, build_idmap_index, add_to_index, load, save
from shared.db import get_all_chunks, get_conn, update_faiss_id
from shared.settings import settings
from shared.logging import get_logger

log = get_logger("embed_index")

INDEX_DIR = settings.index_dir
INDEX_PATH = os.path.join(INDEX_DIR, "bo_pd.index")


def run():
    emb = get_embedder()
    chunks = get_all_chunks()

    if not chunks:
        log.warning("no_chunks_to_index")
        return {"index_dir": INDEX_DIR, "dim": 0, "nvecs": 0, "mode": "skip"}

    # Check if index already exists → incremental or full rebuild
    if os.path.exists(INDEX_PATH):
        try:
            existing_index, existing_metas = load(INDEX_DIR)
            existing_count = existing_index.ntotal
            log.info("existing_index_found", vectors=existing_count)

            # Find new chunks (no faiss_id assigned yet)
            new_chunks = [c for c in chunks if c["faiss_id"] is None]
            if not new_chunks:
                log.info("no_new_chunks_to_index")
                return {"index_dir": INDEX_DIR, "dim": emb.dim, "nvecs": existing_count, "mode": "noop"}

            texts = [c["text"] for c in new_chunks]
            X = emb.encode(texts)
            new_ids = np.arange(
                existing_count + 1,
                existing_count + 1 + len(new_chunks),
                dtype=np.int64,
            )
            add_to_index(existing_index, X, new_ids)

            # Update faiss_id in DB
            for chunk, fid in zip(new_chunks, new_ids.tolist()):
                update_faiss_id(chunk["id"], fid)

            all_metas = existing_metas + [
                {
                    "id": c["doc_id"],
                    "chu_de": c.get("chu_de", ""),
                    "de_muc": c.get("de_muc", ""),
                    "so_dieu": c.get("so_dieu", ""),
                    "tieu_de_dieu": c.get("tieu_de_dieu", ""),
                    "text": c["text"],
                    "chunk_id": f'{c["doc_id"]}#c{c["chunk_index"]}',
                }
                for c in new_chunks
            ]
            save(existing_index, all_metas, INDEX_DIR)
            nvecs = existing_index.ntotal
            log.info("incremental_index_done", added=len(new_chunks), total=nvecs)
            return {"index_dir": INDEX_DIR, "dim": X.shape[1], "nvecs": nvecs, "mode": "incremental"}
        except Exception as e:
            log.warning("incremental_failed_falling_back_to_rebuild", error=str(e))

    # Full rebuild
    texts = [c["text"] for c in chunks]
    metas = [
        {
            "id": c["doc_id"],
            "chu_de": c.get("chu_de", ""),
            "de_muc": c.get("de_muc", ""),
            "so_dieu": c.get("so_dieu", ""),
            "tieu_de_dieu": c.get("tieu_de_dieu", ""),
            "text": c["text"],
            "chunk_id": f'{c["doc_id"]}#c{c["chunk_index"]}',
        }
        for c in chunks
    ]

    X = emb.encode(texts)
    index = build_index(X)
    save(index, metas, INDEX_DIR)

    # Update faiss_id in DB for all chunks
    with get_conn() as conn:
        rows = conn.execute("SELECT id FROM chunks ORDER BY doc_id, chunk_index").fetchall()
        for i, (row,) in enumerate(rows):
            conn.execute("UPDATE chunks SET faiss_id=? WHERE id=?", (i, row))
        conn.commit()

    log.info("full_rebuild_done", nvecs=index.ntotal)
    return {"index_dir": INDEX_DIR, "dim": X.shape[1], "nvecs": index.ntotal, "mode": "full_rebuild"}

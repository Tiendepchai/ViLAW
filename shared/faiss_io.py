import faiss
import json
import os
import numpy as np
from typing import List, Dict, Optional, Tuple

from shared.logging import get_logger

log = get_logger("faiss_io")

INDEX_FILE = "bo_pd.index"
META_FILE = "bo_pd_meta.json"


def build_index(embs: np.ndarray) -> faiss.Index:
    """Build a standalone IndexFlatIP (non-IDMap) for first-time indexing."""
    index = faiss.IndexFlatIP(embs.shape[1])
    faiss.normalize_L2(embs)
    index.add(embs)
    return index


def build_idmap_index(dim: int) -> faiss.Index:
    """Create an IndexIDMap(IndexFlatIP) for incremental add/remove."""
    flat = faiss.IndexFlatIP(dim)
    return faiss.IndexIDMap(flat)


def add_to_index(index: faiss.Index, embs: np.ndarray, ids: np.ndarray) -> None:
    """Add vectors with integer IDs. ids must match embs.shape[0]."""
    faiss.normalize_L2(embs)
    index.add_with_ids(embs, ids)


def remove_from_index(index: faiss.Index, ids: List[int]) -> None:
    """Remove vectors by integer ID."""
    if ids:
        index.remove_ids(np.array(ids, dtype=np.int64))


def save(index: faiss.Index, metas: List[Dict], index_dir: str) -> None:
    os.makedirs(index_dir, exist_ok=True)
    faiss.write_index(index, os.path.join(index_dir, INDEX_FILE))
    with open(os.path.join(index_dir, META_FILE), "w", encoding="utf-8") as f:
        json.dump(metas, f, ensure_ascii=False)
    log.info("index_saved", path=index_dir, vectors=index.ntotal, metas=len(metas))


def load(index_dir: str) -> Tuple[faiss.Index, List[Dict]]:
    idx = faiss.read_index(os.path.join(index_dir, INDEX_FILE))
    with open(os.path.join(index_dir, META_FILE), encoding="utf-8") as f:
        metas = json.load(f)
    log.info("index_loaded", path=index_dir, vectors=idx.ntotal, metas=len(metas))
    return idx, metas

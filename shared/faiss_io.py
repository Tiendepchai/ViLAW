import faiss, json, os, numpy as np
from typing import List, Dict

def build_faiss(embs: np.ndarray):
    index = faiss.IndexFlatIP(embs.shape[1])
    # normalize for IP ~ cosine if not already normalized
    faiss.normalize_L2(embs)
    index.add(embs)
    return index

def save(index, metas: List[Dict], index_dir: str):
    os.makedirs(index_dir, exist_ok=True)
    faiss.write_index(index, os.path.join(index_dir, "bo_pd.index"))
    with open(os.path.join(index_dir, "bo_pd_meta.json"), "w", encoding="utf-8") as f:
        json.dump(metas, f, ensure_ascii=False)

def load(index_dir: str):
    idx = faiss.read_index(os.path.join(index_dir, "bo_pd.index"))
    with open(os.path.join(index_dir, "bo_pd_meta.json"), encoding="utf-8") as f:
        metas = json.load(f)
    return idx, metas


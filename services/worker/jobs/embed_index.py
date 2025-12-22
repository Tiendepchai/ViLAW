import os, json, numpy as np
from shared.embedding import get_embedder
from shared.faiss_io import build_faiss, save
from shared.config import DATA_DIR, INDEX_DIR

INP = os.path.join(DATA_DIR, "bo_pd_chunks.jsonl")

def run():
    emb = get_embedder()
    texts, metas = [], []
    for line in open(INP, encoding="utf-8"):
        d = json.loads(line); texts.append(d["text"]); metas.append(d)
    X = emb.encode(texts)
    index = build_faiss(X)
    save(index, metas, INDEX_DIR)
    return {"index_dir": INDEX_DIR, "dim": X.shape[1], "nvecs": X.shape[0]}


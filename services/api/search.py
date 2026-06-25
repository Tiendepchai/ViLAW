import numpy as np
from shared.faiss_io import load
from shared.embedding import get_embedder
from shared.hybrid import rerank

class Searcher:
    def __init__(self, index_dir):
        self.index, self.metas = load(index_dir)
        self.embed = get_embedder()
    def search(self, q: str, top_k=8):
        qv = self.embed.encode(q)
        faiss = self.index
        # cosine on normalized vectors:
        import faiss as _faiss
        _faiss.normalize_L2(qv)
        D, I = faiss.search(qv, min(top_k*5, 50))
        metas = [self.metas[i] for i in I[0]]
        ranked = rerank(q, metas, D[0])
        return [{"score": float(s), "exact": float(ex), "sim": float(sim), "meta": m} for s,m,sim,ex in ranked[:top_k]]


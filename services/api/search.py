import numpy as np
from shared.faiss_io import load
from shared.embedding import get_embedder
from shared.hybrid import rerank
from shared.logging import get_logger

log = get_logger("search")


class Searcher:
    def __init__(self, index_dir):
        self.index, self.metas = load(index_dir)
        self.embed = get_embedder()

    def search(self, q: str, top_k=8):
        qv = self.embed.encode(q)
        import faiss as _faiss

        _faiss.normalize_L2(qv)
        D, I = self.index.search(qv, min(top_k * 5, 50))
        metas = [self.metas[i] for i in I[0]]
        ranked = rerank(q, metas, D[0])
        results = [
            {"score": float(s), "exact": float(ex), "sim": float(sim), "meta": m}
            for s, m, sim, ex in ranked[:top_k]
        ]
        log.info("search_done", q=q, top_k=top_k, results=len(results))
        return results

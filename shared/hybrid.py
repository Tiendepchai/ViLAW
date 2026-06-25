import re, numpy as np, json
from .text_norm import strip_accents
from .config import DEFAULT_ALPHA, DEFAULT_BETA

PRIORITY = r"\b(điều|khoản|mục|chương|tiểu mục)\b"

def keyword_score(q: str, meta: dict) -> float:
    qn = strip_accents(q.lower())
    keys = [meta.get("so_dieu",""), meta.get("de_muc",""), meta.get("chu_de",""), meta.get("tieu_de_dieu","")]
    keys = [strip_accents(k.lower()) for k in keys if k]
    score = 0.0
    for k in keys:
        if k and k in qn:
            score += 1.0
    return score

def dynamic_alpha_beta(q: str):
    return (0.7, 0.3) if re.search(PRIORITY, q.lower()) else (DEFAULT_ALPHA, DEFAULT_BETA)

def rerank(q: str, metas, sim_scores):
    out = []
    alpha, beta = dynamic_alpha_beta(q)
    for m, s in zip(metas, sim_scores):
        exact = keyword_score(q, m)
        out.append((alpha*exact + beta*float(s), m, s, exact))
    out.sort(key=lambda x: x[0], reverse=True)
    return out


import re
from .text_norm import strip_accents
from .config import DEFAULT_ALPHA, DEFAULT_BETA

# Keywords that signal the query is asking about a specific legal reference
LEGAL_REF = re.compile(
    r"\b(điều|khoản|mục|chương|tiểu mục|điều\s+\d+|khoản\s+\d+)\b",
    re.IGNORECASE,
)
# Keywords for general legal questions (rely more on embedding)
GENERAL_LEGAL = re.compile(
    r"\b(quy định|pháp luật|luật|nghị định|thông tư|hành vi|tội|vi phạm|hình phạt|trách nhiệm|quyền|nghĩa vụ)\b",
    re.IGNORECASE,
)


def keyword_score(q: str, meta: dict) -> float:
    """Compute exact-match keyword score between query and document metadata."""
    qn = strip_accents(q.lower())
    keys = [
        meta.get("so_dieu", ""),
        meta.get("de_muc", ""),
        meta.get("chu_de", ""),
        meta.get("tieu_de_dieu", ""),
        meta.get("section", ""),
    ]
    keys = [strip_accents(k.lower()) for k in keys if k]
    score = 0.0
    for k in keys:
        if k and k in qn:
            score += 1.0
    return score


def dynamic_alpha_beta(q: str):
    """Dynamically adjust keyword vs embedding weights."""
    ql = q.lower()
    if LEGAL_REF.search(ql):
        # Query has specific legal reference → prioritize exact match
        return 0.7, 0.3
    if GENERAL_LEGAL.search(ql):
        # General legal question → more balanced
        return 0.5, 0.5
    # Default
    return DEFAULT_ALPHA, DEFAULT_BETA


def rerank(q: str, metas, sim_scores):
    """Hybrid rerank: combine keyword exact match + embedding similarity."""
    out = []
    alpha, beta = dynamic_alpha_beta(q)
    for m, s in zip(metas, sim_scores):
        exact = keyword_score(q, m)
        combined = alpha * exact + beta * float(s)
        out.append((combined, m, s, exact))
    out.sort(key=lambda x: x[0], reverse=True)
    return out

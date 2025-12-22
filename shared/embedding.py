import numpy as np
from typing import List
import os

class BuiltinEmbedder:
    """Nhẹ: HashingVectorizer + IDF thủ công (fallback)."""
    def __init__(self, n_features=2**15):
        from sklearn.feature_extraction.text import HashingVectorizer
        self.v = HashingVectorizer(n_features=n_features, alternate_sign=False,
                                   norm="l2", ngram_range=(1,2))
        self.dim = n_features
    def encode(self, texts: List[str]) -> np.ndarray:
        if isinstance(texts, str): texts = [texts]
        X = self.v.transform(texts)
        return X.toarray().astype("float32")

def get_embedder():
    backend = os.getenv("EMBEDDER_BACKEND", "builtin")
    if backend == "st":
        from sentence_transformers import SentenceTransformer
        model_name = os.getenv("EMBEDDER_MODEL", "AITeamVN/Vietnamese_Embedding")
        m = SentenceTransformer(model_name)
        class ST:
            dim = m.get_sentence_embedding_dimension()
            def encode(self, texts):
                if isinstance(texts, str): texts = [texts]
                return m.encode(texts, convert_to_numpy=True, normalize_embeddings=True).astype("float32")
        return ST()
    return BuiltinEmbedder()


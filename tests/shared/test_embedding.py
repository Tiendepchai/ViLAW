import os
import pytest
import numpy as np
from shared.embedding import get_embedder


class TestBuiltinEmbedder:
    @pytest.fixture(autouse=True)
    def set_builtin(self):
        os.environ["EMBEDDER_BACKEND"] = "builtin"
        yield

    def test_encode_single_text(self):
        emb = get_embedder()
        vec = emb.encode("Hello world")
        assert isinstance(vec, np.ndarray)
        assert vec.shape[0] == 1  # 2D array even for single text

    def test_encode_multiple_texts(self):
        emb = get_embedder()
        vecs = emb.encode(["Text A", "Text B"])
        assert vecs.shape[0] == 2

    def test_encode_returns_float32(self):
        emb = get_embedder()
        vecs = emb.encode("Test")
        assert vecs.dtype == np.float32

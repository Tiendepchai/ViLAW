import os
import tempfile

import numpy as np
import pytest

from shared.faiss_io import build_index, build_idmap_index, save, load, add_to_index


class TestFaissIO:
    @pytest.fixture
    def index_dir(self):
        d = tempfile.mkdtemp()
        yield d

    @pytest.fixture
    def sample_vectors(self):
        return np.random.rand(10, 64).astype(np.float32)

    def test_save_and_load_roundtrip(self, index_dir, sample_vectors):
        metas = [{"id": f"doc{i}", "text": f"Doc {i}"} for i in range(10)]
        index = build_index(sample_vectors)
        save(index, metas, index_dir)
        assert os.path.exists(os.path.join(index_dir, "bo_pd.index"))
        assert os.path.exists(os.path.join(index_dir, "bo_pd_meta.json"))

        loaded_index, loaded_metas = load(index_dir)
        assert loaded_index.ntotal == 10
        assert len(loaded_metas) == 10
        assert loaded_metas[0]["id"] == "doc0"

    def test_idmap_index(self, index_dir):
        index = build_idmap_index(64)
        assert index.ntotal == 0
        assert index.d == 64

    def test_add_to_idmap(self, index_dir):
        index = build_idmap_index(64)
        embs = np.random.rand(3, 64).astype(np.float32)
        ids = np.array([100, 200, 300], dtype=np.int64)
        add_to_index(index, embs, ids)
        assert index.ntotal == 3

    def test_build_flat_index(self, sample_vectors):
        index = build_index(sample_vectors)
        assert index.ntotal == 10

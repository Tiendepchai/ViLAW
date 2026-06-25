import pytest
from shared.hybrid import keyword_score, dynamic_alpha_beta, rerank


class TestKeywordScore:
    def test_exact_match_so_dieu(self):
        meta = {"so_dieu": "Điều 1"}
        score = keyword_score("theo điều 1 của luật", meta)
        assert score >= 1.0

    def test_no_match(self):
        meta = {"so_dieu": "Điều 99"}
        score = keyword_score("quy định chung", meta)
        assert score == 0.0

    def test_partial_match_de_muc(self):
        meta = {"de_muc": "Hình sự"}
        score = keyword_score("bộ luật hình sự", meta)
        assert score >= 1.0

    def test_accent_insensitive(self):
        meta = {"so_dieu": "Điều 5"}
        score = keyword_score("dieu 5", meta)
        assert score >= 1.0


class TestDynamicAlphaBeta:
    def test_legal_ref_prioritizes_exact(self):
        alpha, beta = dynamic_alpha_beta("theo điều 1 của luật")
        assert alpha > beta
        assert alpha >= 0.6

    def test_general_legal_balanced(self):
        alpha, beta = dynamic_alpha_beta("quy định về pháp luật")
        assert alpha == pytest.approx(beta, abs=0.1)

    def test_general_query_default(self):
        alpha, beta = dynamic_alpha_beta("thời tiết hôm nay thế nào")
        assert alpha == pytest.approx(0.6, abs=0.1)
        assert beta == pytest.approx(0.4, abs=0.1)

    def test_khoan_detected(self):
        alpha, beta = dynamic_alpha_beta("khoản 2 điều 5")
        assert alpha > beta


class TestRerank:
    def test_basic_rerank_returns_sorted(self):
        results = rerank(
            "điều 1",
            [{"so_dieu": "Điều 99"}, {"so_dieu": "Điều 1"}],
            [0.3, 0.5],
        )
        assert len(results) == 2
        # First result should have higher combined score
        assert results[0][0] >= results[1][0]

    def test_rerank_returns_tuple(self):
        results = rerank("test", [{"so_dieu": "Test"}], [0.5])
        combined, meta, sim, exact = results[0]
        assert isinstance(combined, float)
        assert isinstance(meta, dict)
        assert isinstance(sim, float)
        assert isinstance(exact, float)

import pytest
from fastapi.testclient import TestClient

from services.api.app import app

client = TestClient(app)


class TestHealth:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestSearch:
    def test_search_rejects_empty_query(self):
        resp = client.post("/v1/search", json={"q": "", "top_k": 5})
        # Should fail validation (min_length=1)
        assert resp.status_code == 422

    def test_search_rejects_excessively_long_query(self):
        resp = client.post("/v1/search", json={"q": "x" * 2001, "top_k": 5})
        assert resp.status_code == 422

    def test_search_rejects_invalid_top_k(self):
        resp = client.post("/v1/search", json={"q": "test", "top_k": -1})
        assert resp.status_code == 422

    def test_search_rejects_top_k_too_large(self):
        resp = client.post("/v1/search", json={"q": "test", "top_k": 100})
        assert resp.status_code == 422


class TestAsk:
    def test_ask_rejects_empty_query(self):
        resp = client.post("/v1/ask", json={"q": "", "top_k": 5})
        assert resp.status_code == 422

    def test_ask_rejects_missing_query(self):
        resp = client.post("/v1/ask", json={"top_k": 5})
        assert resp.status_code == 422


class TestFeedback:
    def test_feedback_validates_rating_range(self):
        resp = client.post(
            "/v1/feedback",
            json={
                "conversation_id": "conv1",
                "message_id": "msg1",
                "rating": 5,  # must be 0 or 1
            },
        )
        assert resp.status_code == 422

    def test_feedback_ok(self):
        resp = client.post(
            "/v1/feedback",
            json={
                "conversation_id": "conv1",
                "message_id": "msg1",
                "rating": 1,
                "comment": "Good answer",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

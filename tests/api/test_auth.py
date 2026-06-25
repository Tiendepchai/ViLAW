import os
import pytest
from fastapi.testclient import TestClient

from shared.settings import settings


@pytest.fixture
def auth_enabled():
    old = settings.auth_enabled
    settings.auth_enabled = True
    os.environ["AUTH_ENABLED"] = "true"
    yield
    settings.auth_enabled = old
    os.environ.pop("AUTH_ENABLED", None)


class TestAuth:
    def test_login_returns_token(self, auth_enabled):
        # Re-import app with auth enabled
        from services.api.app import app
        client = TestClient(app)
        resp = client.post("/v1/auth/login")
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["token_type"] == "bearer"

    def test_search_without_token_fails(self, auth_enabled):
        from services.api.app import app
        client = TestClient(app)
        resp = client.post("/v1/search", json={"q": "test", "top_k": 5})
        assert resp.status_code == 401
        assert "Missing token" in resp.json()["error"]

    def test_health_public_without_token(self, auth_enabled):
        from services.api.app import app
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200

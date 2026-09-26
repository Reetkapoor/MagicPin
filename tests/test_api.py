from fastapi.testclient import TestClient

from app.api import app
from app.store import state


client = TestClient(app)


def setup_function():
    state.reset()


def test_healthz_and_metadata():
    assert client.get("/v1/healthz").status_code == 200
    assert client.get("/v1/metadata").status_code == 200


def test_context_version_conflict():
    base = {
        "scope": "merchant",
        "context_id": "m_test",
        "version": 1,
        "payload": {"name": "Test"},
        "delivered_at": "2026-09-26T10:00:00Z",
    }
    assert client.post("/v1/context", json=base).status_code == 200
    assert client.post("/v1/context", json=base).status_code == 409

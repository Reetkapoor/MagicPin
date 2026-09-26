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


def test_context_payload_cap():
    payload = {"blob": "x" * (500 * 1024)}
    response = client.post("/v1/context", json={
        "scope": "merchant", "context_id": "large", "version": 1,
        "payload": payload, "delivered_at": "2026-09-26T10:00:00Z",
    })
    assert response.status_code == 400
    assert response.json()["reason"] == "payload_too_large"


def test_tick_timestamp_uses_request_now():
    state.put_context("category", "restaurants", 1, {"slug": "restaurants"})
    state.put_context("merchant", "m1", 1, {
        "merchant_id": "m1", "category_slug": "restaurants",
        "identity": {"name": "Test Cafe", "owner_first_name": "Reet", "locality": "Noida", "city": "Noida"},
        "offers": [], "performance": {}, "subscription": {}, "customer_aggregate": {},
    })
    state.put_context("trigger", "t1", 1, {
        "id": "t1", "kind": "curious_ask_due", "scope": "merchant",
        "merchant_id": "m1", "urgency": 1, "suppression_key": "t1:m1", "payload": {},
    })
    response = client.post("/v1/tick", json={"now": "2026-09-26T10:15:00Z", "available_triggers": ["t1"]})
    assert response.status_code == 200
    assert state.conversations["conv_m1_t1"][0]["ts"] == "2026-09-26T10:15:00Z"

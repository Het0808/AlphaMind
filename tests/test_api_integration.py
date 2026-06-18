"""Integration tests against the FastAPI app via TestClient.

Exercise the production surface — ops endpoints, versioning, auth, rate limiting,
metrics — plus a deterministic business endpoint (/v1/portfolio/advise). No
OpenAI/langgraph required (heavy deps are lazy and these paths don't hit them).
"""

import importlib

import pytest
from fastapi.testclient import TestClient

from alphamind.config import get_settings


@pytest.fixture
def client(monkeypatch):
    # Disable auth/rate limits by default; reload settings + app fresh.
    for var in ["AUTH_ENABLED", "RATE_LIMIT_ENABLED", "API_KEYS"]:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    get_settings.cache_clear()
    import api.main as main
    importlib.reload(main)
    return TestClient(main.app)


def test_health_ready_version(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").json()["status"] in {"ready", "degraded"}
    v = client.get("/version").json()
    assert v["api_version"] == "v1" and "version" in v


def test_metrics_endpoint(client):
    r = client.get("/metrics")
    assert r.status_code == 200


def test_versioned_prefix(client):
    # Business endpoints live under /v1, not at root.
    assert client.post("/portfolio/advise", json={"holdings": []}).status_code == 404
    r = client.post("/v1/portfolio/advise", json={
        "risk_profile": {"risk_tolerance": "BALANCED"},
        "holdings": [
            {"ticker": "NVDA", "weight": 0.5, "sector": "Tech", "recommendation": "BUY", "conviction": 8, "risk_score": 6},
            {"ticker": "AAPL", "weight": 0.5, "sector": "Tech", "recommendation": "HOLD", "conviction": 6, "risk_score": 4},
        ],
    })
    assert r.status_code == 200
    body = r.json()
    assert {p["ticker"] for p in body["positions"]} == {"NVDA", "AAPL"}
    assert "x-request-id" in {k.lower() for k in r.headers}


def test_auth_enforced_when_enabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "secret-key")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    get_settings.cache_clear()
    import api.main as main
    importlib.reload(main)
    c = TestClient(main.app)

    payload = {"risk_profile": {"risk_tolerance": "BALANCED"}, "holdings": [{"ticker": "X", "weight": 1.0}]}
    assert c.post("/v1/portfolio/advise", json=payload).status_code == 401          # no key
    assert c.post("/v1/portfolio/advise", json=payload, headers={"X-API-Key": "wrong"}).status_code == 403
    assert c.post("/v1/portfolio/advise", json=payload, headers={"X-API-Key": "secret-key"}).status_code == 200
    assert c.get("/health").status_code == 200                                       # ops exempt

    get_settings.cache_clear()


def test_rate_limit_returns_429(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "2")
    monkeypatch.setenv("RATE_LIMIT_WINDOW", "60")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    get_settings.cache_clear()
    import api.main as main
    importlib.reload(main)
    c = TestClient(main.app)

    payload = {"risk_profile": {"risk_tolerance": "BALANCED"}, "holdings": [{"ticker": "X", "weight": 1.0}]}
    codes = [c.post("/v1/portfolio/advise", json=payload).status_code for _ in range(3)]
    assert codes[:2] == [200, 200] and codes[2] == 429

    get_settings.cache_clear()

"""E0 smoke test — proves the app boots and the health route responds."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert body["storage"] in {"memory", "postgres"}


def test_root_ok():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["health"] == "/api/health"

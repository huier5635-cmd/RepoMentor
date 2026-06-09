from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def test_langgraph_status_and_debug_api(monkeypatch):
    monkeypatch.setenv("LANGGRAPH_ENABLED", "false")
    get_settings.cache_clear()
    client = TestClient(app)

    status = client.get("/api/graph/status")
    assert status.status_code == 200
    assert status.json()["active_orchestrator"] == "legacy"

    state = client.get("/api/debug/graph/analyze%3Amissing/state")
    assert state.status_code == 200
    assert state.json()["found"] is False

    trace = client.get("/api/debug/graph/analyze%3Amissing/trace")
    assert trace.status_code == 200
    assert trace.json()["events"] == []

    resume = client.post("/api/debug/graph/analyze%3Amissing/resume", json={})
    assert resume.status_code == 200
    assert resume.json()["resumed"] is False

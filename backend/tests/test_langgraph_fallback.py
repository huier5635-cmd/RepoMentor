from __future__ import annotations

import hashlib

from app.core.config import get_settings
from app.core.schemas import AnalyzeRepoResponse
from app.graphs.graph_orchestrator import GraphOrchestrator


class FakeLegacy:
    def __init__(self) -> None:
        self.called = False

    def analyze_repo(self, repo_url: str) -> AnalyzeRepoResponse:
        self.called = True
        return AnalyzeRepoResponse(
            repo_id="fallback-repo",
            repo_url=repo_url,
            status="done",
            graph_summary={},
            worker_outputs=[],
            run_commands=[],
            test_commands=[],
            entrypoints=[],
            session_id="session-fallback",
        )


def test_graph_orchestrator_falls_back_to_legacy(monkeypatch):
    monkeypatch.setenv("LANGGRAPH_ENABLED", "true")
    get_settings.cache_clear()
    legacy = FakeLegacy()
    orchestrator = GraphOrchestrator(legacy)

    def fail(_repo_url: str):
        raise RuntimeError("graph failed")

    monkeypatch.setattr(orchestrator.repo_analysis_graph, "invoke", fail)
    response = orchestrator.analyze_repo("local-repo")

    assert legacy.called is True
    assert response.repo_id == "fallback-repo"
    thread_id = f"analyze:{hashlib.sha1('local-repo'.encode('utf-8')).hexdigest()[:12]}"
    events = orchestrator.get_graph_trace(thread_id)["events"]
    assert any(event["event_type"] == "fallback" for event in events)
    monkeypatch.setenv("LANGGRAPH_ENABLED", "false")
    get_settings.cache_clear()

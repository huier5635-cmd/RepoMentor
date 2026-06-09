from __future__ import annotations

import hashlib
from typing import Any

from app.core.config import get_settings
from app.core.schemas import AnalyzeRepoResponse, FinalAnswer
from app.graphs.checkpoint import get_checkpointer
from app.graphs.graph_trace import TraceEvent, graph_trace_store
from app.graphs.graph_utils import graph_status_payload, thread_id_for_analyze, thread_id_for_qa
from app.graphs.qa_graph import QAGraph
from app.graphs.repo_analysis_graph import RepoAnalysisGraph
from app.graphs.state import RepoMentorState


class GraphOrchestrator:
    def __init__(self, legacy_orchestrator) -> None:
        self.legacy = legacy_orchestrator
        self.repo_analysis_graph = RepoAnalysisGraph(legacy_orchestrator)
        self.qa_graph = QAGraph(legacy_orchestrator)
        self.states: dict[str, RepoMentorState] = {}
        self.session_threads: dict[str, str] = {}
        self.latest_qa_threads_by_repo: dict[str, str] = {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self.legacy, name)

    def analyze_repo(self, repo_url: str) -> AnalyzeRepoResponse:
        settings = get_settings()
        if not settings.langgraph_enabled:
            return self.legacy.analyze_repo(repo_url)
        try:
            response, state = self.repo_analysis_graph.invoke(repo_url)
            self._store_state(state)
            return response
        except Exception as error:
            self._record_fallback(thread_id_for_analyze(self._repo_hash(repo_url)), "repo_analysis_graph", str(error))
            return self.legacy.analyze_repo(repo_url)

    def answer_question(self, repo_id: str, question: str) -> FinalAnswer:
        settings = get_settings()
        if not settings.langgraph_enabled:
            return self.legacy.answer_question(repo_id, question)
        try:
            final, state = self.qa_graph.invoke(repo_id, question)
            self._store_state(state)
            if state.get("session_id"):
                self.session_threads[state["session_id"]] = state["thread_id"]
                self.latest_qa_threads_by_repo[repo_id] = state["thread_id"]
            return final
        except Exception as error:
            self._record_fallback(thread_id_for_qa(repo_id, "fallback"), "qa_graph", str(error))
            return self.legacy.answer_question(repo_id, question)

    def graph_status(self) -> dict[str, Any]:
        settings = get_settings()
        info = get_checkpointer()
        payload = graph_status_payload(
            enabled=settings.langgraph_enabled,
            active="langgraph" if settings.langgraph_enabled else "legacy",
            backend=info.backend,
            available=info.available,
            warning=info.warning,
        )
        payload.update(
            {
                "trace_enabled": settings.langgraph_trace_enabled,
                "max_retries": settings.langgraph_max_retries,
                "graphs": [
                    {"name": self.repo_analysis_graph.graph_name, "nodes": self.repo_analysis_graph.node_order},
                    {"name": self.qa_graph.graph_name, "nodes": self.qa_graph.node_order},
                ],
                "known_threads": sorted(self.states),
            }
        )
        return payload

    def get_graph_state(self, thread_id: str) -> dict[str, Any]:
        state = self.states.get(thread_id) or self._checkpoint_state(thread_id)
        return {"thread_id": thread_id, "state": state or {}, "found": bool(state)}

    def get_graph_trace(self, thread_id: str) -> dict[str, Any]:
        return {"thread_id": thread_id, "events": graph_trace_store.get(thread_id)}

    def resume_thread(self, thread_id: str) -> dict[str, Any]:
        state = self.states.get(thread_id) or self._checkpoint_state(thread_id)
        if not state:
            return {"thread_id": thread_id, "resumed": False, "message": "thread state not found"}
        state["status"] = state.get("status") or "resumed"
        self._store_state(state)
        event = TraceEvent(
            thread_id=thread_id,
            graph_name=str(state.get("current_node") or "graph"),
            node_name="resume",
            event_type="decision",
            output_summary="manual debug resume requested; state restored for inspection",
            evidence_count=len(state.get("retrieved_evidence") or []),
            model_info=state.get("model_info"),
        )
        graph_trace_store.append(thread_id, event)
        return {"thread_id": thread_id, "resumed": True, "state": state}

    def agent_flow_for_repo(self, repo_id: str) -> dict[str, Any]:
        thread_id = thread_id_for_analyze(repo_id)
        state = self.states.get(thread_id) or self._checkpoint_state(thread_id)
        events = graph_trace_store.get(thread_id)
        if state or events:
            return {
                "repo_id": repo_id,
                "mode": "langgraph",
                "thread_id": thread_id,
                "graph_name": "repo_analysis_graph",
                "current_node": (state or {}).get("current_node"),
                "latest_qa_thread_id": self.latest_qa_threads_by_repo.get(repo_id, ""),
                "nodes": self._nodes_from_events(events, self.repo_analysis_graph.node_order),
                "workers": (state or {}).get("worker_outputs", []),
                "retry_count": (state or {}).get("retry_count", 0),
            }
        record = self.legacy.repo_store.load(repo_id)
        return {
            "repo_id": repo_id,
            "mode": "legacy",
            "latest_qa_thread_id": self.latest_qa_threads_by_repo.get(repo_id, ""),
            "workers": [
                {
                    "worker_name": output.worker_name,
                    "status": output.status,
                    "findings": output.findings,
                    "uncertainties": output.uncertainties,
                }
                for output in record.worker_outputs
            ],
        }

    def _store_state(self, state: RepoMentorState) -> None:
        thread_id = state.get("thread_id")
        if thread_id:
            self.states[thread_id] = state

    def _checkpoint_state(self, thread_id: str) -> dict[str, Any] | None:
        for info in [self.repo_analysis_graph.checkpointer, self.qa_graph.checkpointer, get_checkpointer()]:
            saver = info.saver
            if hasattr(saver, "get_state"):
                state = saver.get_state(thread_id)
                if state:
                    return state
        return None

    def _nodes_from_events(self, events: list[dict[str, Any]], node_order: list[str]) -> list[dict[str, Any]]:
        by_node: dict[str, dict[str, Any]] = {
            node: {"node_name": node, "status": "pending", "events": 0, "elapsed_ms": None, "error": ""}
            for node in node_order
        }
        for event in events:
            node = event.get("node_name") or ""
            if node not in by_node:
                by_node[node] = {"node_name": node, "status": "pending", "events": 0, "elapsed_ms": None, "error": ""}
            by_node[node]["events"] += 1
            if event.get("event_type") == "start":
                by_node[node]["status"] = "running"
            if event.get("event_type") in {"success", "checkpoint", "decision"}:
                by_node[node]["status"] = "completed"
            if event.get("event_type") == "error":
                by_node[node]["status"] = "failed"
                by_node[node]["error"] = event.get("error") or ""
            if event.get("elapsed_ms") is not None:
                by_node[node]["elapsed_ms"] = event.get("elapsed_ms")
        return [by_node[node] for node in by_node]

    def _record_fallback(self, thread_id: str, graph_name: str, error: str) -> None:
        event = TraceEvent(
            thread_id=thread_id,
            graph_name=graph_name,
            node_name="fallback",
            event_type="fallback",
            output_summary="LangGraph failed; legacy orchestrator used",
            error=error,
        )
        graph_trace_store.append(thread_id, event)

    def _repo_hash(self, repo_url: str) -> str:
        return hashlib.sha1((repo_url or "unknown").encode("utf-8")).hexdigest()[:12]

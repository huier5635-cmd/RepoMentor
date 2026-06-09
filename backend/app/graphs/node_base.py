from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from app.core.schemas import WorkerOutput
from app.graphs.graph_trace import TraceEvent, graph_trace_store
from app.graphs.state import RepoMentorState, add_trace_event, merge_worker_output_into_state


@dataclass
class GraphNodeResult:
    state_update: dict[str, Any] = field(default_factory=dict)
    worker_output: WorkerOutput | dict[str, Any] | None = None
    trace_event: TraceEvent | dict[str, Any] | None = None
    error: str = ""


def run_graph_node(
    state: RepoMentorState,
    graph_name: str,
    node_name: str,
    fn: Callable[[RepoMentorState], GraphNodeResult | dict[str, Any] | None],
) -> RepoMentorState:
    started = time.perf_counter()
    before_keys = {key: repr(value) for key, value in state.items()}
    thread_id = state.get("thread_id") or "unknown"
    start_event = TraceEvent(
        thread_id=thread_id,
        graph_name=graph_name,
        node_name=node_name,
        event_type="start",
        input_summary=_input_summary(state),
        evidence_count=len(state.get("retrieved_evidence") or []),
        model_info=state.get("model_info"),
    )
    add_trace_event(state, start_event)
    graph_trace_store.append(thread_id, start_event)
    state["current_node"] = node_name
    try:
        result = fn(state)
        if result is None:
            result = GraphNodeResult()
        if isinstance(result, dict):
            result = GraphNodeResult(state_update=result)
        state.update(result.state_update)
        if result.worker_output:
            merge_worker_output_into_state(state, result.worker_output)
        if result.trace_event:
            add_trace_event(state, result.trace_event)
            graph_trace_store.append(thread_id, result.trace_event)
        changed = _changed_keys(before_keys, state)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        success_event = TraceEvent(
            thread_id=thread_id,
            graph_name=graph_name,
            node_name=node_name,
            event_type="success",
            elapsed_ms=elapsed_ms,
            output_summary=_output_summary(state, changed),
            state_keys_changed=changed,
            evidence_count=len(state.get("retrieved_evidence") or []),
            model_info=state.get("model_info"),
        )
        add_trace_event(state, success_event)
        graph_trace_store.append(thread_id, success_event)
        return state
    except Exception as error:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        payload = {
            "node_name": node_name,
            "error": str(error),
            "error_type": type(error).__name__,
            "elapsed_ms": elapsed_ms,
        }
        state["worker_errors"] = [*(state.get("worker_errors") or []), payload]
        state["failed_workers"] = sorted({*(state.get("failed_workers") or []), node_name})
        state["status"] = "failed" if node_name in {"repo_fetch_node", "init_analysis_node"} else state.get("status", "partial")
        error_event = TraceEvent(
            thread_id=thread_id,
            graph_name=graph_name,
            node_name=node_name,
            event_type="error",
            elapsed_ms=elapsed_ms,
            error=str(error),
            evidence_count=len(state.get("retrieved_evidence") or []),
            model_info=state.get("model_info"),
        )
        add_trace_event(state, error_event)
        graph_trace_store.append(thread_id, error_event)
        return state


def _input_summary(state: RepoMentorState) -> str:
    return f"repo_id={state.get('repo_id') or ''}; question={state.get('user_question') or ''}; status={state.get('status')}"


def _output_summary(state: RepoMentorState, changed: list[str]) -> str:
    return f"status={state.get('status')}; changed={', '.join(changed[:8])}"


def _changed_keys(before: dict[str, str], state: RepoMentorState) -> list[str]:
    changed: list[str] = []
    for key, value in state.items():
        if before.get(key) != repr(value):
            changed.append(key)
    return changed


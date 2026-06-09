from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict
from uuid import uuid4

from app.core.schemas import SharedWorkingMemory, WorkerOutput
from app.graphs.graph_trace import TraceEvent


class RepoMentorState(TypedDict, total=False):
    schema_version: str
    thread_id: str
    session_id: str
    repo_id: str | None
    repo_url: str | None
    user_question: str | None
    task_type: str | None
    status: str
    repo_snapshot: dict[str, Any] | None
    repository_graph: dict[str, Any] | None
    hybrid_index_status: dict[str, Any] | None
    worker_plan: list[dict[str, Any]]
    worker_outputs: list[dict[str, Any]]
    worker_errors: list[dict[str, Any]]
    completed_workers: list[str]
    failed_workers: list[str]
    retrieved_evidence: list[dict[str, Any]]
    intermediate_conclusions: list[str]
    unresolved_uncertainties: list[str]
    retrieval_results: list[dict[str, Any]]
    draft_answer: dict[str, Any] | None
    self_check: dict[str, Any] | None
    final_answer: dict[str, Any] | None
    optimizer_changes: list[str]
    model_info: dict[str, Any] | None
    graph_trace: list[dict[str, Any]]
    current_node: str | None
    retry_count: int
    started_at: str | None
    updated_at: str | None
    elapsed_ms: int | None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_initial_state(
    thread_id: str,
    repo_id: str | None = None,
    repo_url: str | None = None,
    user_question: str | None = None,
    session_id: str | None = None,
    task_type: str | None = None,
    status: str = "initialized",
) -> RepoMentorState:
    timestamp = now_iso()
    return {
        "schema_version": "repomentor.langgraph.v1",
        "thread_id": thread_id,
        "session_id": session_id or str(uuid4()),
        "repo_id": repo_id,
        "repo_url": repo_url,
        "user_question": user_question,
        "task_type": task_type,
        "status": status,
        "repo_snapshot": None,
        "repository_graph": None,
        "hybrid_index_status": None,
        "worker_plan": [],
        "worker_outputs": [],
        "worker_errors": [],
        "completed_workers": [],
        "failed_workers": [],
        "retrieved_evidence": [],
        "intermediate_conclusions": [],
        "unresolved_uncertainties": [],
        "retrieval_results": [],
        "draft_answer": None,
        "self_check": None,
        "final_answer": None,
        "optimizer_changes": [],
        "model_info": None,
        "graph_trace": [],
        "current_node": None,
        "retry_count": 0,
        "started_at": timestamp,
        "updated_at": timestamp,
        "elapsed_ms": None,
    }


def merge_worker_output_into_state(state: RepoMentorState, worker_output: WorkerOutput | dict[str, Any] | None) -> RepoMentorState:
    if not worker_output:
        return state
    payload = worker_output.model_dump(mode="json") if isinstance(worker_output, WorkerOutput) else dict(worker_output)
    outputs = list(state.get("worker_outputs") or [])
    if not any(item.get("worker_name") == payload.get("worker_name") for item in outputs):
        outputs.append(payload)
    state["worker_outputs"] = outputs
    evidence = list(state.get("retrieved_evidence") or [])
    seen = {item.get("evidence_id") for item in evidence}
    for item in payload.get("evidence") or []:
        evidence_id = item.get("evidence_id")
        if evidence_id and evidence_id not in seen:
            evidence.append(item)
            seen.add(evidence_id)
    state["retrieved_evidence"] = evidence
    status = payload.get("status")
    worker_name = payload.get("worker_name") or "unknown"
    if status == "failed":
        failed = set(state.get("failed_workers") or [])
        failed.add(worker_name)
        state["failed_workers"] = sorted(failed)
    else:
        completed = set(state.get("completed_workers") or [])
        completed.add(worker_name)
        state["completed_workers"] = sorted(completed)
    state["updated_at"] = now_iso()
    return state


def add_trace_event(state: RepoMentorState, event: TraceEvent | dict[str, Any]) -> RepoMentorState:
    payload = event.model_dump(mode="json") if isinstance(event, TraceEvent) else dict(event)
    state["graph_trace"] = [*(state.get("graph_trace") or []), payload]
    state["current_node"] = payload.get("node_name")
    state["updated_at"] = now_iso()
    return state


def state_to_shared_memory(state: RepoMentorState) -> SharedWorkingMemory:
    return SharedWorkingMemory(
        session_id=state.get("session_id") or "",
        current_task=state.get("repo_id") or state.get("task_type") or "",
        user_question=state.get("user_question") or "",
        retrieved_evidence=state.get("retrieved_evidence") or [],
        intermediate_conclusions=state.get("intermediate_conclusions") or [],
        unresolved_uncertainties=state.get("unresolved_uncertainties") or [],
        worker_outputs=state.get("worker_outputs") or [],
        final_decision_trace=[
            f"{item.get('node_name')}:{item.get('event_type')}"
            for item in state.get("graph_trace") or []
        ],
        model_calls=[state["model_info"]] if state.get("model_info") else [],
        final_answer_json=state.get("final_answer") or {},
    )


def shared_memory_to_state(memory: SharedWorkingMemory, thread_id: str, repo_id: str | None = None) -> RepoMentorState:
    state = create_initial_state(
        thread_id=thread_id,
        repo_id=repo_id,
        user_question=memory.user_question,
        session_id=memory.session_id,
        task_type=memory.current_task,
    )
    state["retrieved_evidence"] = [item.model_dump(mode="json") for item in memory.retrieved_evidence]
    state["worker_outputs"] = [item.model_dump(mode="json") for item in memory.worker_outputs]
    state["intermediate_conclusions"] = list(memory.intermediate_conclusions)
    state["unresolved_uncertainties"] = list(memory.unresolved_uncertainties)
    state["model_info"] = memory.model_calls[-1].model_dump(mode="json") if memory.model_calls else None
    state["final_answer"] = memory.final_answer_json
    return state


from __future__ import annotations

from fastapi import APIRouter

from app.core.orchestrator_provider import get_active_orchestrator, get_graph_orchestrator


router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/repos/{repo_id}/data-layer")
def get_data_layer(repo_id: str) -> dict[str, object]:
    orchestrator = get_active_orchestrator()
    record = orchestrator.repo_store.load(repo_id)
    index = orchestrator._index_for(record)
    graph_summary = orchestrator._graph_summary(record.graph)
    return {
        "repo_id": repo_id,
        "snapshot": record.snapshot,
        "graph_summary": graph_summary,
        "files": record.graph.files,
        "symbols": record.graph.symbols,
        "imports": record.graph.imports,
        "tests": record.graph.tests,
        "docs": record.graph.docs,
        "edges": record.graph.edges,
        "build_scripts": record.graph.build_scripts,
        "development_workflow": record.graph.development_workflow,
        "quality_commands": record.graph.quality_commands,
        "ci_rules": record.graph.ci_rules,
        "worker_outputs": record.worker_outputs,
        "chunks_count": len(record.chunks),
        "evidence_count": len(record.evidence),
        "index": index.summary(),
        "api_raw_response": {
            "snapshot": record.snapshot,
            "graph": record.graph,
            "worker_outputs": record.worker_outputs,
        },
    }


@router.get("/repos/{repo_id}/worker-outputs")
def get_worker_outputs(repo_id: str) -> dict[str, object]:
    orchestrator = get_active_orchestrator()
    record = orchestrator.repo_store.load(repo_id)
    return {"repo_id": repo_id, "worker_outputs": record.worker_outputs}


@router.get("/repos/{repo_id}/repository-graph")
def get_repository_graph(repo_id: str) -> dict[str, object]:
    orchestrator = get_active_orchestrator()
    record = orchestrator.repo_store.load(repo_id)
    return {
        "repo_id": repo_id,
        "snapshot": record.snapshot,
        "graph": record.graph,
        "files": record.graph.files,
        "symbols": record.graph.symbols,
        "imports": record.graph.imports,
        "tests": record.graph.tests,
        "docs": record.graph.docs,
        "entrypoints": record.graph.entrypoints,
        "commands": {
            "setup": record.graph.setup_commands,
            "run": record.graph.run_commands,
            "test": record.graph.test_commands,
            "build": record.graph.build_commands,
            "lint": record.graph.lint_commands,
            "format": record.graph.format_commands,
            "type_check": record.graph.type_check_commands,
        },
        "quality_commands": record.graph.quality_commands,
        "development_workflow": record.graph.development_workflow,
        "issues": record.snapshot.issues,
    }


@router.get("/repos/{repo_id}/agent-flow")
def get_agent_flow(repo_id: str) -> dict[str, object]:
    return get_graph_orchestrator().agent_flow_for_repo(repo_id)


@router.get("/session/{session_id}/memory")
def get_debug_memory(session_id: str) -> dict[str, object]:
    return get_active_orchestrator().get_trace(session_id)


@router.get("/session/{session_id}/retrieval-trace")
def get_retrieval_trace(session_id: str) -> dict[str, object]:
    orchestrator = get_active_orchestrator()
    trace = orchestrator.get_trace(session_id)
    return {
        "session_id": session_id,
        "retrieved_evidence": trace.get("retrieved_evidence", []),
        "final_decision_trace": trace.get("final_decision_trace", []),
    }


@router.get("/session/{session_id}/self-check")
def get_self_check(session_id: str) -> dict[str, object]:
    orchestrator = get_active_orchestrator()
    trace = orchestrator.get_trace(session_id)
    final_answer = trace.get("final_answer_json") or {}
    return final_answer.get("self_check") or {}


@router.get("/session/{session_id}/final-answer-json")
def get_final_answer_json(session_id: str) -> dict[str, object]:
    orchestrator = get_active_orchestrator()
    trace = orchestrator.get_trace(session_id)
    return trace.get("final_answer_json") or {}


@router.get("/graph/{thread_id}/state")
def get_debug_graph_state(thread_id: str) -> dict[str, object]:
    return get_graph_orchestrator().get_graph_state(thread_id)


@router.get("/graph/{thread_id}/trace")
def get_debug_graph_trace(thread_id: str) -> dict[str, object]:
    return get_graph_orchestrator().get_graph_trace(thread_id)


@router.post("/graph/{thread_id}/resume")
def resume_debug_graph(thread_id: str) -> dict[str, object]:
    return get_graph_orchestrator().resume_thread(thread_id)

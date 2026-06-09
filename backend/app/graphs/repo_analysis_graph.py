from __future__ import annotations

import hashlib
from typing import Any

from app.core.schemas import (
    AnalyzeRepoResponse,
    CodeExplanationWorkerInput,
    DependencyWorkerInput,
    DevelopmentWorkflowWorkerInput,
    DocsWorkerInput,
    IssueWorkerInput,
    RepoGraphWorkerInput,
    RepositoryRecord,
    SymbolWorkerInput,
    TestWorkerInput,
)
from app.data_layer.hybrid_retrieval_index import HybridRetrievalIndex
from app.data_layer.repository_intelligence_graph import RepositoryIntelligenceGraphStore
from app.graphs.checkpoint import get_checkpointer
from app.graphs.graph_trace import TraceEvent, graph_trace_store
from app.graphs.graph_utils import thread_id_for_analyze
from app.graphs.node_base import GraphNodeResult, run_graph_node
from app.graphs.state import RepoMentorState, add_trace_event, create_initial_state
from app.workers.code_explanation_worker import CodeExplanationWorker
from app.workers.dependency_worker import DependencyWorker
from app.workers.development_workflow_worker import DevelopmentWorkflowWorker
from app.workers.docs_worker import DocsWorker
from app.workers.issue_worker import IssueWorker
from app.workers.repo_graph_worker import RepoGraphWorker
from app.workers.symbol_worker import SymbolWorker
from app.workers.test_worker import TestWorker


class RepoAnalysisGraph:
    graph_name = "repo_analysis_graph"

    def __init__(self, legacy_orchestrator) -> None:
        self.legacy = legacy_orchestrator
        self.checkpointer = get_checkpointer()
        self._runtime: dict[str, dict[str, Any]] = {}
        self.node_order = [
            "init_analysis_node",
            "repo_fetch_node",
            "repo_graph_node",
            "symbol_node",
            "dependency_node",
            "docs_node",
            "test_node",
            "issue_node",
            "development_workflow_node",
            "code_explanation_node",
            "build_hybrid_index_node",
            "finalize_analysis_node",
        ]

    def invoke(self, repo_url: str) -> tuple[AnalyzeRepoResponse, RepoMentorState]:
        initial_repo_hash = hashlib.sha1((repo_url or "unknown").encode("utf-8")).hexdigest()[:12]
        initial_thread = thread_id_for_analyze(initial_repo_hash)
        state = create_initial_state(thread_id=initial_thread, repo_url=repo_url, status="running")
        for node_name in self.node_order:
            if state.get("status") == "failed" and node_name != "finalize_analysis_node":
                break
            state = run_graph_node(state, self.graph_name, node_name, getattr(self, node_name))
            self._put_checkpoint(state["thread_id"], state)
        response = self._runtime.get(state["thread_id"], {}).get("response")
        if not response:
            errors = state.get("worker_errors") or []
            detail = errors[-1].get("error") if errors else "RepoAnalysisGraph did not produce a response"
            raise RuntimeError(detail)
        return response, state

    def init_analysis_node(self, state: RepoMentorState) -> GraphNodeResult:
        thread_id = state["thread_id"]
        self._runtime[thread_id] = {
            "graph_store": RepositoryIntelligenceGraphStore(),
            "chunks": [],
            "evidence": [],
            "worker_outputs": [],
        }
        plan = [{"node_name": item, "status": "pending"} for item in self.node_order]
        return GraphNodeResult({"worker_plan": plan, "status": "running"})

    def repo_fetch_node(self, state: RepoMentorState) -> GraphNodeResult:
        prepared = self.legacy.git_service.prepare_repository(state.get("repo_url") or "")
        new_thread_id = thread_id_for_analyze(prepared.repo_id)
        if new_thread_id != state["thread_id"]:
            self._runtime[new_thread_id] = self._runtime.pop(state["thread_id"])
            state["thread_id"] = new_thread_id
        self._runtime[state["thread_id"]]["prepared"] = prepared
        memory = self.legacy.memory_store.start_session(prepared.repo_id, "analyze_repo")
        self._runtime[state["thread_id"]]["memory"] = memory
        return GraphNodeResult(
            {
                "thread_id": state["thread_id"],
                "repo_id": prepared.repo_id,
                "repo_url": prepared.repo_url,
                "session_id": memory.session_id,
            }
        )

    def repo_graph_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        prepared = runtime["prepared"]
        result = RepoGraphWorker().run(
            RepoGraphWorkerInput(
                repo_id=prepared.repo_id,
                repo_url=prepared.repo_url,
                local_path=prepared.local_path,
                owner=prepared.owner,
                name=prepared.name,
                default_branch=prepared.default_branch,
            )
        )
        runtime["repo_graph_result"] = result
        runtime["graph_store"].merge(result.graph)
        runtime["chunks"].extend(result.chunks)
        runtime["worker_outputs"].append(result.worker_output)
        self.legacy.memory_store.add_worker_output(runtime["memory"].session_id, result.worker_output)
        return GraphNodeResult(
            {
                "repo_snapshot": result.repo_snapshot.model_dump(mode="json"),
                "repository_graph": runtime["graph_store"].graph.model_dump(mode="json"),
            },
            worker_output=result.worker_output,
        )

    def symbol_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        graph_store = runtime["graph_store"]
        result = SymbolWorker().run(SymbolWorkerInput(local_path=runtime["prepared"].local_path, files=graph_store.graph.files))
        graph_store.add_symbols(result.symbols)
        graph_store.add_edges(result.edges)
        runtime["chunks"].extend(result.chunks)
        runtime["worker_outputs"].append(result.worker_output)
        self.legacy.memory_store.add_worker_output(runtime["memory"].session_id, result.worker_output)
        return GraphNodeResult({"repository_graph": graph_store.graph.model_dump(mode="json")}, worker_output=result.worker_output)

    def dependency_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        graph_store = runtime["graph_store"]
        result = DependencyWorker().run(DependencyWorkerInput(local_path=runtime["prepared"].local_path, files=graph_store.graph.files))
        graph_store.add_edges(result.imports)
        runtime["worker_outputs"].append(result.worker_output)
        self.legacy.memory_store.add_worker_output(runtime["memory"].session_id, result.worker_output)
        return GraphNodeResult({"repository_graph": graph_store.graph.model_dump(mode="json")}, worker_output=result.worker_output)

    def docs_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        graph_store = runtime["graph_store"]
        result = DocsWorker().run(DocsWorkerInput(local_path=runtime["prepared"].local_path, files=graph_store.graph.files, graph=graph_store.graph))
        graph_store.add_files(result.docs)
        graph_store.add_edges(result.edges)
        runtime["chunks"].extend(result.chunks)
        runtime["evidence"].extend(result.worker_output.evidence)
        runtime["worker_outputs"].append(result.worker_output)
        self.legacy.memory_store.add_worker_output(runtime["memory"].session_id, result.worker_output)
        return GraphNodeResult({"repository_graph": graph_store.graph.model_dump(mode="json")}, worker_output=result.worker_output)

    def test_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        graph_store = runtime["graph_store"]
        result = TestWorker().run(TestWorkerInput(files=graph_store.graph.files, graph=graph_store.graph))
        graph_store.add_edges(result.tests)
        graph_store.graph.test_commands = sorted(set(graph_store.graph.test_commands + result.test_commands))
        runtime["worker_outputs"].append(result.worker_output)
        self.legacy.memory_store.add_worker_output(runtime["memory"].session_id, result.worker_output)
        return GraphNodeResult({"repository_graph": graph_store.graph.model_dump(mode="json")}, worker_output=result.worker_output)

    def issue_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        prepared = runtime["prepared"]
        result = IssueWorker().run(IssueWorkerInput(repo_url=prepared.repo_url, owner=prepared.owner, name=prepared.name))
        runtime["repo_graph_result"].repo_snapshot.issues = result.issues
        runtime["chunks"].extend(result.chunks)
        runtime["evidence"].extend(result.worker_output.evidence)
        runtime["worker_outputs"].append(result.worker_output)
        self.legacy.memory_store.add_worker_output(runtime["memory"].session_id, result.worker_output)
        return GraphNodeResult({"repo_snapshot": runtime["repo_graph_result"].repo_snapshot.model_dump(mode="json")}, worker_output=result.worker_output)

    def development_workflow_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        graph_store = runtime["graph_store"]
        result = DevelopmentWorkflowWorker().run(
            DevelopmentWorkflowWorkerInput(
                repo_snapshot=runtime["repo_graph_result"].repo_snapshot,
                graph=graph_store.graph,
                chunks=runtime["chunks"],
            )
        )
        graph_store.set_development_workflow(result.guide)
        runtime["chunks"].extend(result.chunks)
        runtime["evidence"].extend(result.guide.evidence)
        runtime["worker_outputs"].append(result.worker_output)
        self.legacy.memory_store.add_worker_output(runtime["memory"].session_id, result.worker_output)
        self.legacy.memory_store.add_development_workflow(runtime["memory"].session_id, result.guide)
        return GraphNodeResult({"repository_graph": graph_store.graph.model_dump(mode="json")}, worker_output=result.worker_output)

    def code_explanation_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        result = CodeExplanationWorker().run(
            CodeExplanationWorkerInput(
                question=runtime["prepared"].name or "repository overview",
                graph=runtime["graph_store"].graph,
                chunks=runtime["chunks"],
            )
        )
        runtime["worker_outputs"].append(result.output)
        self.legacy.memory_store.add_worker_output(runtime["memory"].session_id, result.output)
        return GraphNodeResult(worker_output=result.output)

    def build_hybrid_index_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        index = HybridRetrievalIndex()
        index.build(runtime["chunks"])
        self.legacy.indexes[state["repo_id"]] = index
        runtime["index"] = index
        return GraphNodeResult({"hybrid_index_status": index.summary()})

    def finalize_analysis_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        prepared = runtime["prepared"]
        graph_store = runtime["graph_store"]
        record = RepositoryRecord(
            repo_id=prepared.repo_id,
            snapshot=runtime["repo_graph_result"].repo_snapshot,
            graph=graph_store.graph,
            chunks=runtime["chunks"],
            evidence=runtime["evidence"],
            worker_outputs=runtime["worker_outputs"],
        )
        self.legacy.repo_store.save(record)
        summary = graph_store.summary()
        summary.update(runtime["index"].summary())
        summary["shared_memory"] = {
            "session_id": runtime["memory"].session_id,
            "worker_outputs": len(runtime["worker_outputs"]),
            "retrieved_evidence": len(self.legacy.memory_store.get_memory(runtime["memory"].session_id).retrieved_evidence),
        }
        primary_language = next(iter(graph_store.graph.languages), "")
        response = AnalyzeRepoResponse(
            repo_id=prepared.repo_id,
            repo_url=prepared.repo_url,
            owner=prepared.owner,
            name=prepared.name,
            default_branch=prepared.default_branch,
            local_path=prepared.local_path,
            status="done",
            files=graph_store.graph.files,
            file_tree=graph_store.graph.files,
            graph_summary=summary,
            languages=graph_store.graph.languages,
            primary_language=primary_language,
            core_directories=graph_store.graph.core_directories,
            key_files=runtime["repo_graph_result"].repo_snapshot.key_files,
            readme_exists=any(item.name.lower().startswith("readme") for item in graph_store.graph.files),
            worker_outputs=runtime["worker_outputs"],
            setup_commands=graph_store.graph.setup_commands,
            run_commands=graph_store.graph.run_commands,
            test_commands=graph_store.graph.test_commands,
            build_commands=graph_store.graph.build_commands,
            lint_commands=graph_store.graph.lint_commands,
            format_commands=graph_store.graph.format_commands,
            type_check_commands=graph_store.graph.type_check_commands,
            entrypoints=graph_store.graph.entrypoints,
            issues_count=len(runtime["repo_graph_result"].repo_snapshot.issues),
            session_id=runtime["memory"].session_id,
        )
        runtime["response"] = response
        return GraphNodeResult(
            {
                "repo_snapshot": record.snapshot.model_dump(mode="json"),
                "repository_graph": record.graph.model_dump(mode="json"),
                "status": "completed",
            }
        )

    def _put_checkpoint(self, thread_id: str, state: RepoMentorState) -> None:
        saver = self.checkpointer.saver
        if hasattr(saver, "put_state"):
            saver.put_state(thread_id, state)
        event = TraceEvent(
            thread_id=thread_id,
            graph_name=self.graph_name,
            node_name=state.get("current_node") or "checkpoint",
            event_type="checkpoint",
            output_summary=f"checkpoint saved for {thread_id}",
            evidence_count=len(state.get("retrieved_evidence") or []),
            model_info=state.get("model_info"),
        )
        add_trace_event(state, event)
        graph_trace_store.append(thread_id, event)

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.schemas import CodeExplanationWorkerInput, FinalAnswer, TaskType, TestWorkerInput
from app.graphs.checkpoint import get_checkpointer
from app.graphs.graph_trace import TraceEvent, graph_trace_store
from app.graphs.graph_utils import thread_id_for_qa
from app.graphs.node_base import GraphNodeResult, run_graph_node
from app.graphs.state import RepoMentorState, add_trace_event, create_initial_state, merge_worker_output_into_state
from app.workers.code_explanation_worker import CodeExplanationWorker
from app.workers.test_worker import TestWorker


class QAGraph:
    graph_name = "qa_graph"

    def __init__(self, legacy_orchestrator) -> None:
        self.legacy = legacy_orchestrator
        self.checkpointer = get_checkpointer()
        self._runtime: dict[str, dict[str, Any]] = {}
        self.node_order = [
            "init_qa_node",
            "intent_router_node",
            "retrieval_node",
            "worker_context_node",
            "answer_generator_node",
            "evaluator_node",
            "optimizer_node",
            "final_answer_node",
        ]

    def invoke(self, repo_id: str, question: str) -> tuple[FinalAnswer, RepoMentorState]:
        initial_session_id = ""
        thread_id = thread_id_for_qa(repo_id, "pending")
        state = create_initial_state(
            thread_id=thread_id,
            repo_id=repo_id,
            user_question=question,
            status="running",
        )
        for node_name in self.node_order[:-2]:
            state = run_graph_node(state, self.graph_name, node_name, getattr(self, node_name))
            self._put_checkpoint(state["thread_id"], state)
            if node_name == "init_qa_node":
                initial_session_id = state["session_id"]
            if state.get("status") == "failed":
                break

        state = self._maybe_retry_or_route(state)
        for node_name in self.node_order[-2:]:
            state = run_graph_node(state, self.graph_name, node_name, getattr(self, node_name))
            self._put_checkpoint(state["thread_id"], state)
        final = self._runtime.get(state["thread_id"], {}).get("final_answer")
        if not final:
            errors = state.get("worker_errors") or []
            detail = errors[-1].get("error") if errors else "QAGraph did not produce a final answer"
            raise RuntimeError(detail)
        if initial_session_id and state["thread_id"] != thread_id_for_qa(repo_id, initial_session_id):
            self._runtime.pop(thread_id_for_qa(repo_id, "pending"), None)
        return final, state

    def init_qa_node(self, state: RepoMentorState) -> GraphNodeResult:
        record = self.legacy.repo_store.load(state["repo_id"] or "")
        index = self.legacy._index_for(record)
        memory = self.legacy.memory_store.start_session(record.repo_id, state.get("user_question") or "")
        thread_id = thread_id_for_qa(record.repo_id, memory.session_id)
        self._runtime[thread_id] = {
            "record": record,
            "index": index,
            "memory": memory,
            "bundle": None,
            "self_check": None,
            "final_answer": None,
        }
        return GraphNodeResult(
            {
                "thread_id": thread_id,
                "repo_id": record.repo_id,
                "session_id": memory.session_id,
                "repository_graph": record.graph.model_dump(mode="json"),
                "worker_plan": [{"node_name": item, "status": "pending"} for item in self.node_order],
            }
        )

    def intent_router_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        task_type = self.legacy.intent_router.classify(state.get("user_question") or "")
        runtime["task_type"] = task_type
        runtime["memory"].current_task = task_type.value
        runtime["memory"].final_decision_trace.append(f"intent router classified task as {task_type.value}")
        self.legacy.task_planner.plan(task_type)
        decision = self._decision_event(state, "intent_router_node", f"task_type={task_type.value}")
        return GraphNodeResult({"task_type": task_type.value}, trace_event=decision)

    def retrieval_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        task_type: TaskType = runtime["task_type"]
        results = runtime["index"].hybrid_search(
            self.legacy._query_for(task_type, state.get("user_question") or ""),
            filters=self.legacy._filters_for(task_type),
            top_k=10,
        )
        for result in results:
            self.legacy.memory_store.add_evidence(runtime["memory"].session_id, result.evidence)
        memory = self.legacy.memory_store.get_memory(runtime["memory"].session_id)
        return GraphNodeResult(
            {
                "retrieval_results": [
                    {"chunk_id": item.chunk.chunk_id, "score": item.score, "source_type": item.chunk.source_type.value}
                    for item in results
                ],
                "retrieved_evidence": [item.model_dump(mode="json") for item in memory.retrieved_evidence],
            }
        )

    def worker_context_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        task_type: TaskType = runtime["task_type"]
        record = runtime["record"]
        session_id = runtime["memory"].session_id
        if task_type == TaskType.CODE_EXPLANATION:
            code_result = CodeExplanationWorker().run(
                CodeExplanationWorkerInput(question=state.get("user_question") or "", graph=record.graph, chunks=record.chunks)
            )
            self.legacy.memory_store.add_worker_output(session_id, code_result.output)
            return GraphNodeResult(worker_output=code_result.output)
        if task_type == TaskType.TEST_MAPPING:
            test_output = TestWorker().run(TestWorkerInput(files=record.graph.files, graph=record.graph)).worker_output
            self.legacy.memory_store.add_worker_output(session_id, test_output)
            return GraphNodeResult(worker_output=test_output)
        if task_type == TaskType.ISSUE_RECOMMENDATION:
            self._reuse_worker_output(state, record, session_id, "Issue Worker")
        elif task_type == TaskType.DEVELOPMENT_WORKFLOW:
            for worker_name in ["Docs Worker", "Issue Worker", "Test Worker", "Development Workflow Worker"]:
                self._reuse_worker_output(state, record, session_id, worker_name)
            if record.graph.development_workflow:
                self.legacy.memory_store.add_development_workflow(session_id, record.graph.development_workflow)
        memory = self.legacy.memory_store.get_memory(session_id)
        return GraphNodeResult(
            {
                "worker_outputs": [item.model_dump(mode="json") for item in memory.worker_outputs],
                "retrieved_evidence": [item.model_dump(mode="json") for item in memory.retrieved_evidence],
            }
        )

    def answer_generator_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        task_type: TaskType = runtime["task_type"]
        record = runtime["record"]
        memory = self.legacy.memory_store.get_memory(runtime["memory"].session_id)
        deterministic_bundle = self.legacy.candidate_generator.generate(task_type, memory, record.graph)
        bundle = self.legacy._maybe_generate_llm_answer(task_type, state.get("user_question") or "", memory, record.graph, deterministic_bundle)
        if bundle.model_info.prompt_type != "not_called":
            self.legacy.memory_store.add_model_call(memory.session_id, bundle.model_info)
        runtime["bundle"] = bundle
        return GraphNodeResult(
            {
                "draft_answer": bundle.model_dump(mode="json"),
                "model_info": bundle.model_info.model_dump(mode="json"),
                "intermediate_conclusions": [*(state.get("intermediate_conclusions") or []), bundle.conclusion],
            }
        )

    def evaluator_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        bundle = runtime["bundle"]
        self_check = self.legacy.evaluator.evaluate(bundle, runtime["record"].graph)
        runtime["self_check"] = self_check
        runtime["memory"].final_decision_trace.append(f"evaluator suggested {self_check.suggested_action.value}")
        decision = self._decision_event(state, "evaluator_node", f"suggested_action={self_check.suggested_action.value}")
        return GraphNodeResult({"self_check": self_check.model_dump(mode="json")}, trace_event=decision)

    def retrieve_more_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        task_type: TaskType = runtime["task_type"]
        retry_count = int(state.get("retry_count") or 0) + 1
        query = f"{state.get('user_question') or ''} README docs config command source tests workflow"
        results = runtime["index"].hybrid_search(query, filters=self.legacy._filters_for(task_type), top_k=16)
        for result in results:
            self.legacy.memory_store.add_evidence(runtime["memory"].session_id, result.evidence)
        memory = self.legacy.memory_store.get_memory(runtime["memory"].session_id)
        retry_event = TraceEvent(
            thread_id=state["thread_id"],
            graph_name=self.graph_name,
            node_name="retrieve_more_node",
            event_type="retry",
            output_summary=f"retry_count={retry_count}; retrieved={len(results)}",
            evidence_count=len(memory.retrieved_evidence),
            model_info=state.get("model_info"),
        )
        return GraphNodeResult(
            {
                "retry_count": retry_count,
                "retrieval_results": [
                    {"chunk_id": item.chunk.chunk_id, "score": item.score, "source_type": item.chunk.source_type.value}
                    for item in results
                ],
                "retrieved_evidence": [item.model_dump(mode="json") for item in memory.retrieved_evidence],
            },
            trace_event=retry_event,
        )

    def optimizer_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        memory = self.legacy.memory_store.get_memory(runtime["memory"].session_id)
        final = self.legacy.optimizer.optimize(runtime["bundle"], runtime["self_check"], memory.final_decision_trace)
        memory.final_decision_trace.append("optimizer produced final answer")
        runtime["final_answer"] = final
        return GraphNodeResult(
            {
                "final_answer": final.model_dump(mode="json"),
                "optimizer_changes": memory.final_decision_trace[-4:],
                "status": "completed",
            }
        )

    def final_answer_node(self, state: RepoMentorState) -> GraphNodeResult:
        runtime = self._runtime[state["thread_id"]]
        final = runtime["final_answer"]
        self.legacy.memory_store.add_final_answer(runtime["memory"].session_id, final)
        return GraphNodeResult({"final_answer": final.model_dump(mode="json"), "status": "completed"})

    def _maybe_retry_or_route(self, state: RepoMentorState) -> RepoMentorState:
        settings = get_settings()
        suggested = (state.get("self_check") or {}).get("suggested_action")
        retry_count = int(state.get("retry_count") or 0)
        while suggested == "retrieve_more" and retry_count < settings.langgraph_max_retries:
            state = run_graph_node(state, self.graph_name, "retrieve_more_node", self.retrieve_more_node)
            self._put_checkpoint(state["thread_id"], state)
            state = run_graph_node(state, self.graph_name, "answer_generator_node", self.answer_generator_node)
            self._put_checkpoint(state["thread_id"], state)
            state = run_graph_node(state, self.graph_name, "evaluator_node", self.evaluator_node)
            self._put_checkpoint(state["thread_id"], state)
            retry_count = int(state.get("retry_count") or 0)
            suggested = (state.get("self_check") or {}).get("suggested_action")
        return state

    def _reuse_worker_output(self, state: RepoMentorState, record, session_id: str, worker_name: str) -> None:
        output = next((item for item in record.worker_outputs if item.worker_name == worker_name), None)
        if output:
            self.legacy.memory_store.add_worker_output(session_id, output)
            merge_worker_output_into_state(state, output)

    def _decision_event(self, state: RepoMentorState, node_name: str, summary: str) -> TraceEvent:
        return TraceEvent(
            thread_id=state["thread_id"],
            graph_name=self.graph_name,
            node_name=node_name,
            event_type="decision",
            output_summary=summary,
            evidence_count=len(state.get("retrieved_evidence") or []),
            model_info=state.get("model_info"),
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

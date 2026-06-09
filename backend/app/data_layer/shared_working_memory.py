from __future__ import annotations

from uuid import uuid4

from app.core.schemas import (
    ContributingRule,
    DevelopmentWorkflowGuide,
    EvidenceItem,
    FinalAnswer,
    ModelInfo,
    QualityCommand,
    SharedWorkingMemory,
    WorkerOutput,
)


class SharedWorkingMemoryStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SharedWorkingMemory] = {}

    def start_session(self, repo_id: str, question: str) -> SharedWorkingMemory:
        session_id = str(uuid4())
        memory = SharedWorkingMemory(
            session_id=session_id,
            current_task=repo_id,
            user_question=question,
            final_decision_trace=[f"session started for repo {repo_id}"],
        )
        self._sessions[session_id] = memory
        return memory

    def add_worker_output(self, session_id: str, output: WorkerOutput) -> None:
        memory = self._sessions[session_id]
        memory.worker_outputs.append(output)
        memory.final_decision_trace.append(f"{output.worker_name}: {output.status.value}")
        for item in output.evidence:
            self.add_evidence(session_id, item)

    def add_evidence(self, session_id: str, evidence: EvidenceItem) -> None:
        memory = self._sessions[session_id]
        if any(item.evidence_id == evidence.evidence_id for item in memory.retrieved_evidence):
            return
        memory.retrieved_evidence.append(evidence)

    def add_conclusion(self, session_id: str, conclusion: str) -> None:
        memory = self._sessions[session_id]
        memory.intermediate_conclusions.append(conclusion)

    def add_uncertainty(self, session_id: str, uncertainty: str) -> None:
        memory = self._sessions[session_id]
        memory.unresolved_uncertainties.append(uncertainty)

    def add_model_call(self, session_id: str, model_info: ModelInfo) -> None:
        memory = self._sessions[session_id]
        memory.model_calls.append(model_info)
        memory.final_decision_trace.append(
            "llm call "
            f"provider={model_info.provider} model={model_info.model} "
            f"prompt_type={model_info.prompt_type} evidence_count={model_info.evidence_count} "
            f"success={model_info.success} fallback_to_mock={model_info.fallback_to_mock}"
        )

    def add_final_answer(self, session_id: str, answer: FinalAnswer) -> None:
        memory = self._sessions[session_id]
        memory.final_answer_json = answer.model_dump(mode="json")

    def add_development_workflow(self, session_id: str, guide: DevelopmentWorkflowGuide) -> None:
        memory = self._sessions[session_id]
        memory.development_workflow_findings.extend(guide.contribution_steps)
        memory.quality_commands.extend(
            guide.development_commands
            + guide.test_commands
            + guide.lint_commands
            + guide.format_commands
            + guide.type_check_commands
            + guide.build_commands
        )
        memory.contributing_rules.extend(
            guide.branch_rules
            + guide.commit_rules
            + guide.contribution_rules
            + guide.code_style_rules
            + guide.setup_rules
            + guide.test_rules
            + guide.documentation_references
            + guide.project_safety_policies
        )
        memory.ci_findings.extend([rule.workflow_file for rule in guide.ci_rules])
        memory.workflow_uncertainties.extend(guide.uncertainties)
        for item in guide.evidence:
            self.add_evidence(session_id, item)

    def get_memory(self, session_id: str) -> SharedWorkingMemory:
        return self._sessions[session_id]

    def export_trace(self, session_id: str) -> dict[str, object]:
        memory = self.get_memory(session_id)
        return {
            "session_id": memory.session_id,
            "current_task": memory.current_task,
            "user_question": memory.user_question,
            "retrieved_evidence": memory.retrieved_evidence,
            "intermediate_conclusions": memory.intermediate_conclusions,
            "unresolved_uncertainties": memory.unresolved_uncertainties,
            "worker_outputs": memory.worker_outputs,
            "final_decision_trace": memory.final_decision_trace,
            "development_workflow_findings": memory.development_workflow_findings,
            "quality_commands": memory.quality_commands,
            "contributing_rules": memory.contributing_rules,
            "ci_findings": memory.ci_findings,
            "workflow_uncertainties": memory.workflow_uncertainties,
            "model_calls": memory.model_calls,
            "final_answer_json": memory.final_answer_json,
        }

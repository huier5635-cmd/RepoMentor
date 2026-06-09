from __future__ import annotations

from app.core.schemas import AnswerBundle, EvidenceItem, FinalAnswer, SelfCheckReport, SourceType


class EvidenceFormatter:
    def format(self, bundle: AnswerBundle, self_check: SelfCheckReport, trace_summary: list[str]) -> FinalAnswer:
        evidence_docs = self._filter(bundle.evidence, {SourceType.DOCS})
        evidence_code = self._filter(bundle.evidence, {SourceType.CODE, SourceType.TEST, SourceType.TESTS, SourceType.CONFIG, SourceType.BUILD})
        evidence_issues = self._filter(bundle.evidence, {SourceType.ISSUE, SourceType.ISSUES})
        evidence_graph = self._filter(bundle.evidence, {SourceType.GRAPH})
        evidence_workflow = self._filter(
            bundle.evidence,
            {SourceType.WORKFLOW, SourceType.CONTRIBUTING, SourceType.CI, SourceType.STYLE, SourceType.PR_TEMPLATE},
        )
        evidence_commands = self._filter(bundle.evidence, {SourceType.COMMAND})
        evidence_internal_tasks = self._filter(bundle.evidence, {SourceType.INTERNAL_SUGGESTION})
        return FinalAnswer(
            conclusion=bundle.conclusion,
            evidence_docs=evidence_docs,
            evidence_code=evidence_code,
            evidence_issues=evidence_issues,
            evidence_graph=evidence_graph,
            evidence_workflow=evidence_workflow,
            evidence_commands=evidence_commands,
            evidence_internal_tasks=evidence_internal_tasks,
            steps=bundle.steps,
            risks=bundle.risks,
            uncertainties=bundle.uncertainties,
            verifiable_commands=bundle.verifiable_commands,
            self_check=self_check,
            trace_summary=trace_summary,
            model_info=bundle.model_info,
        )

    def _filter(self, evidence: list[EvidenceItem], source_types: set[SourceType]) -> list[EvidenceItem]:
        return [item for item in evidence if item.source_type in source_types]

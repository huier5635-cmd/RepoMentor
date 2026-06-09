from __future__ import annotations

from app.answer.evidence_formatter import EvidenceFormatter
from app.core.schemas import AnswerBundle, FinalAnswer, SelfCheckReport


class Optimizer:
    def __init__(self) -> None:
        self.formatter = EvidenceFormatter()

    def optimize(self, bundle: AnswerBundle, self_check: SelfCheckReport, trace_summary: list[str]) -> FinalAnswer:
        if not self_check.passed:
            if self_check.missing_evidence and "证据不足" not in bundle.conclusion:
                bundle.conclusion = f"当前证据不足：{bundle.conclusion}"
            if self_check.hallucination_risks:
                bundle.risks.extend(risk for risk in self_check.hallucination_risks if risk not in bundle.risks)
                bundle.uncertainties.append("部分模型输出或候选结论缺少证据支持，已降低置信度。")
            if self_check.conflicts:
                bundle.uncertainties.extend(item for item in self_check.conflicts if item not in bundle.uncertainties)
            bundle.confidence = min(bundle.confidence, 0.45)
            if not bundle.evidence:
                bundle.steps = bundle.steps[:2]
        return self.formatter.format(bundle, self_check, trace_summary)

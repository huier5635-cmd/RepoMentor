from __future__ import annotations

from app.core.schemas import CodeExplanationWorkerInput, CodeExplanationWorkerResult, EvidenceItem, SourceType, WorkerOutput, WorkerStatus
from app.data_layer.repository_intelligence_graph import RepositoryIntelligenceGraphStore
from app.services.evidence_service import EvidenceService
from app.workers.base_worker import BaseWorker


class CodeExplanationWorker(BaseWorker[CodeExplanationWorkerInput, CodeExplanationWorkerResult]):
    worker_name = "Code Explanation Worker"

    def __init__(self) -> None:
        self.evidence = EvidenceService()

    def run(self, worker_input: CodeExplanationWorkerInput) -> CodeExplanationWorkerResult:
        graph_store = RepositoryIntelligenceGraphStore(worker_input.graph)
        related = graph_store.get_related_context(worker_input.question)
        evidence: list[EvidenceItem] = []
        findings: list[str] = []
        for symbol in related["symbols"][:5]:
            findings.append(f"{symbol.name} is defined in {symbol.file_path}:{symbol.line_start}")
            evidence.append(
                self.evidence.make(
                    SourceType.CODE,
                    f"{symbol.file_path}::{symbol.name}",
                    symbol.signature or symbol.name,
                    "symbol exists in deterministic symbol graph",
                    file_path=symbol.file_path,
                    line_start=symbol.line_start,
                    line_end=symbol.line_end,
                )
            )
        for edge in related["edges"][:5]:
            findings.append(f"{edge.source} {edge.edge_type.value} {edge.target}")
            evidence.append(
                self.evidence.make(
                    SourceType.CODE,
                    f"{edge.source}->{edge.target}",
                    edge.evidence,
                    "relationship exists in repository intelligence graph",
                    file_path=edge.source,
                    confidence=edge.confidence,
                )
            )
        status = WorkerStatus.SUCCESS if findings else WorkerStatus.PARTIAL
        output = WorkerOutput(
            worker_name=self.worker_name,
            task="explain module/function using graph, symbols, imports, docs and tests evidence",
            status=status,
            findings=findings or ["current graph did not contain a direct match for the requested code target"],
            evidence=evidence,
            uncertainties=[] if findings else ["code target is ambiguous or absent from parsed symbols/files"],
            next_actions=["retrieve more docs/code chunks if evidence coverage is low"],
        )
        return CodeExplanationWorkerResult(output=output)

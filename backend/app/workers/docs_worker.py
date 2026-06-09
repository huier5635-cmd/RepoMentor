from __future__ import annotations

import re
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.core.schemas import ChunkDoc, DocsWorkerInput, DocsWorkerResult, EdgeType, GraphEdge, SourceType, WorkerOutput, WorkerStatus
from app.services.evidence_service import EvidenceService
from app.services.parser_service import ParserService
from app.workers.base_worker import BaseWorker


class DocsWorker(BaseWorker[DocsWorkerInput, DocsWorkerResult]):
    worker_name = "Docs Worker"

    def __init__(self) -> None:
        self.parser = ParserService()
        self.evidence = EvidenceService()

    def run(self, worker_input: DocsWorkerInput) -> DocsWorkerResult:
        docs = [item for item in worker_input.files if item.file_type.value.startswith("docs")]
        chunks: list[ChunkDoc] = []
        edges: list[GraphEdge] = []
        root = Path(worker_input.local_path)
        source_paths = {
            item.path
            for item in worker_input.files
            if item.file_type.value in {"source", "source_frontend", "source_frontend_style", "test"}
        }
        symbols = worker_input.graph.symbols if worker_input.graph else []
        for doc in docs:
            text = self.parser.read_text(root / doc.path)
            chunks.extend(self._chunk_doc(doc.path, text))
            if doc.file_type.value not in {"docs", "docs_static"}:
                continue
            lowered_text = text.lower()
            for source_path in source_paths:
                source_lower = source_path.lower()
                module_name = source_lower.removesuffix(Path(source_lower).suffix).replace("/", ".")
                if source_lower in lowered_text:
                    edges.append(
                        GraphEdge(
                            source=doc.path,
                            target=source_path,
                            edge_type=EdgeType.MENTIONS,
                            evidence=f"{doc.path} explicitly mentions file path {source_path}",
                            confidence=0.9,
                        )
                    )
                elif module_name and module_name in lowered_text:
                    edges.append(
                        GraphEdge(
                            source=doc.path,
                            target=source_path,
                            edge_type=EdgeType.DOCUMENTS,
                            evidence=f"{doc.path} mentions module name {module_name}",
                            confidence=0.75,
                        )
                    )
            for symbol in symbols:
                name = symbol.name.split(".")[-1]
                if len(name) < 6 or name.lower() in {"result", "results", "scenario", "status", "config", "error", "risk"}:
                    continue
                if re.search(rf"(?<![\w.]){re.escape(name.lower())}(?![\w.])", lowered_text):
                    edges.append(
                        GraphEdge(
                            source=doc.path,
                            target=symbol.file_path,
                            edge_type=EdgeType.DOCUMENTS,
                            evidence=f"{doc.path} mentions symbol {symbol.name}",
                            confidence=0.7,
                        )
                    )
            edges.extend(self._filename_mapping_edges(doc.path, source_paths))
        edges = self._dedupe_edges(edges)
        output = WorkerOutput(
            worker_name=self.worker_name,
            task="parse README/docs/examples/contributing/changelog",
            status=WorkerStatus.SUCCESS if docs else WorkerStatus.PARTIAL,
            findings=[f"found {len(docs)} docs files", f"created {len(chunks)} docs chunks", f"created {len(edges)} docs edges"],
            evidence=[
                self.evidence.make(
                    SourceType.DOCS,
                    doc.path,
                    doc.content_preview,
                    "documentation file discovered",
                    file_path=doc.path,
                    line_start=1,
                    line_end=min(doc.line_count or 1, 80),
                )
                for doc in docs[:8]
                if doc.content_preview
            ],
            uncertainties=[] if docs else ["no documentation files found"],
            next_actions=["use docs chunks for setup and learning path answers"],
        )
        return DocsWorkerResult(docs=docs, chunks=chunks, edges=edges, worker_output=output)

    def _filename_mapping_edges(self, doc_path: str, source_paths: set[str]) -> list[GraphEdge]:
        mapping = {
            "docs/architecture.md": ["src/agent/resilience_agent.py"],
            "docs/memory_eval.md": ["src/memory/policy.py"],
            "docs/academic_evaluation.md": ["src/evaluation/academic_metrics.py"],
            "docs/benchmark_eval_report.md": ["scripts/run_academic_eval.py"],
            "docs/stress_test_report.md": ["scripts/run_stress_test.py"],
        }
        edges: list[GraphEdge] = []
        for target in mapping.get(doc_path.lower(), []):
            if target in source_paths:
                edges.append(
                    GraphEdge(
                        source=doc_path,
                        target=target,
                        edge_type=EdgeType.DOCUMENTS,
                        evidence=f"{doc_path} filename convention maps to {target}",
                        confidence=0.65,
                    )
                )
        return edges

    def _dedupe_edges(self, edges: list[GraphEdge]) -> list[GraphEdge]:
        by_key: dict[tuple[str, str, EdgeType], GraphEdge] = {}
        for edge in edges:
            key = (edge.source, edge.target, edge.edge_type)
            existing = by_key.get(key)
            if existing is None or edge.confidence > existing.confidence:
                by_key[key] = edge
        return list(by_key.values())

    def _chunk_doc(self, file_path: str, text: str) -> list[ChunkDoc]:
        chunks: list[ChunkDoc] = []
        paragraphs = [para.strip() for para in text.split("\n\n") if para.strip()]
        current_line = 1
        for index, paragraph in enumerate(paragraphs[:80]):
            line_count = paragraph.count("\n") + 1
            chunks.append(
                ChunkDoc(
                    chunk_id=str(uuid5(NAMESPACE_URL, f"doc:{file_path}:{index}")),
                    source_type=SourceType.DOCS,
                    file_path=file_path,
                    title=f"{file_path} section {index + 1}",
                    text=paragraph[:1500],
                    line_start=current_line,
                    line_end=current_line + line_count - 1,
                    metadata={"file_type": "docs", "language": "markdown"},
                )
            )
            current_line += line_count + 1
        return chunks

from __future__ import annotations

from pathlib import Path

from app.core.schemas import EdgeType, GraphEdge, TestWorkerInput, TestWorkerResult, WorkerOutput, WorkerStatus
from app.workers.base_worker import BaseWorker


class TestWorker(BaseWorker[TestWorkerInput, TestWorkerResult]):
    worker_name = "Test Worker"

    def run(self, worker_input: TestWorkerInput) -> TestWorkerResult:
        files_by_path = {item.path: item for item in worker_input.files}
        test_files = [item for item in worker_input.files if item.file_type.value == "test"]
        source_files = [item for item in worker_input.files if item.file_type.value in {"source", "source_frontend", "source_frontend_style"}]
        edges: list[GraphEdge] = []
        for test_file in test_files:
            edges.extend(self._import_edges(test_file.path, worker_input.graph.imports, files_by_path))
            edges.extend(self._filename_edges(test_file.path, source_files))
            edges.extend(self._keyword_edges(test_file.path, source_files))
        edges = self._dedupe_edges(edges)
        test_commands = worker_input.graph.test_commands or self._fallback_commands(worker_input.files)
        output = WorkerOutput(
            worker_name=self.worker_name,
            task="identify test files, test edges and test command candidates",
            status=WorkerStatus.SUCCESS if test_files or test_commands else WorkerStatus.PARTIAL,
            findings=[f"found {len(test_files)} test files", f"created {len(edges)} test edges"],
            uncertainties=[] if edges else ["test-to-source mapping is heuristic until explicit coverage data is available"],
            next_actions=["use test edges for changed-file test mapping"],
        )
        return TestWorkerResult(tests=edges, test_commands=sorted(set(test_commands)), worker_output=output)

    def _candidate_source_paths(self, test_path: str) -> list[str]:
        name = Path(test_path).name
        stem = Path(test_path).stem
        for prefix in ("test_",):
            if stem.startswith(prefix):
                stem = stem[len(prefix) :]
        stem = stem.removesuffix(".test").removesuffix(".spec")
        candidates = []
        for ext in (".py", ".js", ".jsx", ".ts", ".tsx"):
            candidates.extend([f"{stem}{ext}", f"src/{stem}{ext}", f"app/{stem}{ext}"])
        return candidates

    def _import_edges(self, test_path: str, imports: list[GraphEdge], files_by_path: dict[str, object]) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        for edge in imports:
            if edge.source != test_path:
                continue
            target = files_by_path.get(edge.target)
            if not target or getattr(target, "file_type").value == "test":
                continue
            edges.append(
                GraphEdge(
                    source=test_path,
                    target=edge.target,
                    edge_type=EdgeType.TESTS,
                    evidence=f"high confidence: {test_path} imports {edge.target}; {edge.evidence}",
                    confidence=0.95,
                )
            )
        return edges

    def _filename_edges(self, test_path: str, source_files: list) -> list[GraphEdge]:
        stem = self._source_stem(test_path)
        if not stem:
            return []
        edges: list[GraphEdge] = []
        for source in source_files:
            if Path(source.path).stem == stem:
                edges.append(
                    GraphEdge(
                        source=test_path,
                        target=source.path,
                        edge_type=EdgeType.TESTS,
                        evidence=f"medium confidence: {test_path} filename exactly matches {source.path}",
                        confidence=0.75,
                    )
                )
        return edges

    def _keyword_edges(self, test_path: str, source_files: list) -> list[GraphEdge]:
        stem = self._source_stem(test_path)
        if not stem:
            return []
        explicit = {
            "academic_metrics": ["src/evaluation/academic_metrics.py"],
            "memory_policy": ["src/memory/policy.py"],
            "safety_contract": ["src/safety/contract.py"],
            "risk_signal_detection": ["src/safety/risk.py", "scripts/resilience_copilot_baseline.py"],
            "json_export": ["src/utils/io.py", "scripts/export_results.py"],
        }
        source_by_path = {item.path: item for item in source_files}
        edges: list[GraphEdge] = []
        for target in explicit.get(stem, []):
            if target in source_by_path:
                edges.append(
                    GraphEdge(
                        source=test_path,
                        target=target,
                        edge_type=EdgeType.TESTS,
                        evidence=f"low confidence: {test_path} matches known keyword mapping {stem} -> {target}",
                        confidence=0.55,
                    )
                )
        keywords = [part for part in stem.split("_") if len(part) >= 3]
        if not keywords:
            return edges
        for source in source_files:
            lowered = source.path.lower()
            hits = [keyword for keyword in keywords if keyword in lowered]
            if hits and len(hits) >= max(1, len(keywords) - 1):
                edges.append(
                    GraphEdge(
                        source=test_path,
                        target=source.path,
                        edge_type=EdgeType.TESTS,
                        evidence=f"low confidence: {test_path} keywords {', '.join(hits)} match {source.path}",
                        confidence=0.45,
                    )
                )
        return edges

    def _source_stem(self, test_path: str) -> str:
        stem = Path(test_path).stem
        if stem.startswith("test_"):
            stem = stem[len("test_") :]
        stem = stem.removesuffix(".test").removesuffix(".spec")
        return stem.lower()

    def _dedupe_edges(self, edges: list[GraphEdge]) -> list[GraphEdge]:
        by_key: dict[tuple[str, str, EdgeType], GraphEdge] = {}
        for edge in edges:
            key = (edge.source, edge.target, edge.edge_type)
            existing = by_key.get(key)
            if existing is None or edge.confidence > existing.confidence:
                by_key[key] = edge
        return list(by_key.values())

    def _fallback_commands(self, files: list) -> list[str]:
        languages = {item.language for item in files}
        commands = []
        if "python" in languages:
            commands.extend(["pytest", "python -m pytest"])
        if {"javascript", "typescript"} & languages:
            commands.extend(["npm test", "npm run test", "pnpm test", "yarn test"])
        return commands

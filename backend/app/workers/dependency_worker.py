from __future__ import annotations

from app.core.schemas import DependencyWorkerInput, DependencyWorkerResult, WorkerOutput, WorkerStatus
from app.services.parser_service import ParserService
from app.workers.base_worker import BaseWorker


class DependencyWorker(BaseWorker[DependencyWorkerInput, DependencyWorkerResult]):
    worker_name = "Dependency Worker"

    def __init__(self) -> None:
        self.parser = ParserService()

    def run(self, worker_input: DependencyWorkerInput) -> DependencyWorkerResult:
        imports = []
        unresolved = []
        source_files = [item for item in worker_input.files if item.language in {"python", "javascript", "typescript"}]
        for file_node in source_files:
            parsed_edges, parsed_unresolved = self.parser.parse_imports(worker_input.local_path, file_node)
            imports.extend(parsed_edges)
            unresolved.extend(parsed_unresolved)
        status = WorkerStatus.SUCCESS if imports or not source_files else WorkerStatus.PARTIAL
        output = WorkerOutput(
            worker_name=self.worker_name,
            task="extract import edges and unresolved imports",
            status=status,
            findings=[f"resolved {len(imports)} local imports", f"marked {len(unresolved)} unresolved imports"],
            uncertainties=unresolved[:20],
            next_actions=["use import graph for module explanation"],
        )
        return DependencyWorkerResult(imports=imports, unresolved_imports=unresolved, worker_output=output)

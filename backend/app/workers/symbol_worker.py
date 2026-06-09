from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from app.core.schemas import ChunkDoc, SourceType, SymbolWorkerInput, SymbolWorkerResult, WorkerOutput, WorkerStatus
from app.services.parser_service import ParserService
from app.workers.base_worker import BaseWorker


class SymbolWorker(BaseWorker[SymbolWorkerInput, SymbolWorkerResult]):
    worker_name = "Symbol Worker"

    def __init__(self) -> None:
        self.parser = ParserService()

    def run(self, worker_input: SymbolWorkerInput) -> SymbolWorkerResult:
        symbols = []
        edges = []
        chunks: list[ChunkDoc] = []
        source_files = [item for item in worker_input.files if item.language in {"python", "javascript", "typescript"}]
        for file_node in source_files:
            parsed_symbols, parsed_edges = self.parser.parse_symbols(worker_input.local_path, file_node)
            symbols.extend(parsed_symbols)
            edges.extend(parsed_edges)
            for symbol in parsed_symbols:
                chunks.append(
                    ChunkDoc(
                        chunk_id=str(uuid5(NAMESPACE_URL, f"symbol:{symbol.file_path}:{symbol.name}:{symbol.line_start}")),
                        source_type=SourceType.CODE,
                        file_path=symbol.file_path,
                        symbol_name=symbol.name,
                        title=symbol.signature or symbol.name,
                        text=" ".join(part for part in [symbol.signature, symbol.docstring] if part) or symbol.name,
                        line_start=symbol.line_start,
                        line_end=symbol.line_end,
                        metadata={"language": symbol.language, "symbol_type": symbol.symbol_type.value},
                    )
                )
        output = WorkerOutput(
            worker_name=self.worker_name,
            task="extract deterministic symbols and defines edges",
            status=WorkerStatus.SUCCESS if symbols else WorkerStatus.PARTIAL,
            findings=[f"extracted {len(symbols)} symbols from {len(source_files)} source files"],
            uncertainties=[] if symbols else ["no symbols found; repository may be non-code or parser coverage is limited"],
            next_actions=["run Dependency Worker", "use symbols for code explanation"],
        )
        return SymbolWorkerResult(symbols=symbols, edges=edges, chunks=chunks, worker_output=output)

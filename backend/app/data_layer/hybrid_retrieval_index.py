from __future__ import annotations

from uuid import uuid5, NAMESPACE_URL

from app.core.schemas import ChunkDoc, EvidenceItem, RetrievalFilters, RetrievalResult, SourceType
from app.data_layer.keyword_index import KeywordIndex
from app.data_layer.metadata_filter import MetadataFilter
from app.data_layer.vector_index import VectorIndex


class HybridRetrievalIndex:
    def __init__(self) -> None:
        self.keyword_index = KeywordIndex()
        self.vector_index = VectorIndex()
        self.metadata_filter = MetadataFilter()
        self._chunks: dict[str, ChunkDoc] = {}

    def build(self, chunks: list[ChunkDoc]) -> None:
        self._chunks = {chunk.chunk_id: chunk for chunk in chunks}
        self.keyword_index.build(chunks)
        self.vector_index.build(chunks)

    def summary(self) -> dict[str, object]:
        return {
            "keyword_index_count": self.keyword_index.count(),
            "vector_index_status": self.vector_index.status,
            "metadata_filter_status": self.metadata_filter.status,
        }

    def hybrid_search(
        self,
        query: str,
        filters: RetrievalFilters | None = None,
        top_k: int = 8,
    ) -> list[RetrievalResult]:
        keyword_results = self.keyword_index.search(query, top_k=top_k)
        vector_results = self.vector_index.search(query, top_k=top_k)
        scores: dict[str, float] = {}
        for chunk, score in keyword_results:
            scores[chunk.chunk_id] = max(scores.get(chunk.chunk_id, 0.0), score)
        for chunk, score in vector_results:
            scores[chunk.chunk_id] = max(scores.get(chunk.chunk_id, 0.0), score)

        filtered_ids = {chunk.chunk_id for chunk in self.metadata_filter.apply(list(self._chunks.values()), filters)}
        ranked_ids = [chunk_id for chunk_id, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)]
        results: list[RetrievalResult] = []
        for chunk_id in ranked_ids:
            if chunk_id not in filtered_ids:
                continue
            chunk = self._chunks[chunk_id]
            source_type = chunk.source_type
            if source_type == SourceType.ISSUE:
                source_type = SourceType.ISSUES
            evidence = EvidenceItem(
                evidence_id=str(uuid5(NAMESPACE_URL, f"{chunk.chunk_id}:{query}")),
                source_type=source_type,
                source_ref=chunk.title or chunk.file_path or str(chunk.issue_number),
                file_path=chunk.file_path,
                issue_number=chunk.issue_number,
                line_start=chunk.line_start,
                line_end=chunk.line_end,
                quote=chunk.text[:500],
                supports_claim=f"retrieved for query: {query}",
                confidence=min(1.0, scores[chunk_id] / 3.0),
            )
            results.append(RetrievalResult(chunk=chunk, evidence=evidence, score=scores[chunk_id]))
            if len(results) >= top_k:
                break
        return results

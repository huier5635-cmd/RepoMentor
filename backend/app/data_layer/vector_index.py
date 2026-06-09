from __future__ import annotations

from app.core.schemas import ChunkDoc
from app.data_layer.keyword_index import KeywordIndex


class VectorIndex:
    def __init__(self) -> None:
        self._chunks: list[ChunkDoc] = []

    @property
    def status(self) -> str:
        return "simple_similarity_fallback"

    def build(self, chunks: list[ChunkDoc]) -> None:
        self._chunks = chunks

    def search(self, query: str, top_k: int = 8) -> list[tuple[ChunkDoc, float]]:
        query_terms = set(KeywordIndex._tokens(query))
        if not query_terms:
            return []
        scored: list[tuple[ChunkDoc, float]] = []
        for chunk in self._chunks:
            terms = set(KeywordIndex._tokens(" ".join([chunk.title, chunk.text, chunk.file_path])))
            if not terms:
                continue
            score = len(query_terms & terms) / len(query_terms | terms)
            if score > 0:
                scored.append((chunk, score))
        return sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]

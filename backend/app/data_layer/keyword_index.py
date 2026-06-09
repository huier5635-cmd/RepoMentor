from __future__ import annotations

import re
from collections import defaultdict

from app.core.schemas import ChunkDoc


class KeywordIndex:
    def __init__(self) -> None:
        self._chunks: dict[str, ChunkDoc] = {}
        self._posting: dict[str, set[str]] = defaultdict(set)

    def build(self, chunks: list[ChunkDoc]) -> None:
        self._chunks.clear()
        self._posting.clear()
        for chunk in chunks:
            self.add(chunk)

    def add(self, chunk: ChunkDoc) -> None:
        self._chunks[chunk.chunk_id] = chunk
        text = " ".join(
            [
                chunk.title,
                chunk.text,
                chunk.file_path,
                chunk.symbol_name,
                " ".join(str(value) for value in chunk.metadata.values()),
            ]
        )
        for token in self._tokens(text):
            self._posting[token].add(chunk.chunk_id)

    def search(self, query: str, top_k: int = 8) -> list[tuple[ChunkDoc, float]]:
        scores: dict[str, float] = defaultdict(float)
        for token in self._tokens(query):
            for chunk_id in self._posting.get(token, set()):
                scores[chunk_id] += 2.0
        for chunk_id, chunk in self._chunks.items():
            if query.lower() in chunk.text.lower() or query.lower() in chunk.title.lower():
                scores[chunk_id] += 1.0
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
        return [(self._chunks[chunk_id], score) for chunk_id, score in ranked]

    def count(self) -> int:
        return len(self._chunks)

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [item for item in re.split(r"[^a-zA-Z0-9_\-\u4e00-\u9fff]+", text.lower()) if item]

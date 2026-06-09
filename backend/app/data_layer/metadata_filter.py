from __future__ import annotations

from app.core.schemas import ChunkDoc, RetrievalFilters


class MetadataFilter:
    @property
    def status(self) -> str:
        return "enabled"

    def apply(self, chunks: list[ChunkDoc], filters: RetrievalFilters | None) -> list[ChunkDoc]:
        if filters is None:
            return chunks
        result = chunks
        if filters.source_type:
            allowed = set(filters.source_type)
            result = [chunk for chunk in result if chunk.source_type.value in allowed]
        if filters.language:
            allowed = set(filters.language)
            result = [chunk for chunk in result if chunk.metadata.get("language") in allowed]
        if filters.file_type:
            allowed = set(filters.file_type)
            result = [chunk for chunk in result if chunk.metadata.get("file_type") in allowed]
        if filters.labels:
            labels = set(filters.labels)
            result = [
                chunk
                for chunk in result
                if labels.intersection(set(chunk.metadata.get("labels", [])))
            ]
        if filters.command_type:
            allowed = set(filters.command_type)
            result = [chunk for chunk in result if chunk.metadata.get("command_type") in allowed]
        if filters.rule_type:
            allowed = set(filters.rule_type)
            result = [chunk for chunk in result if chunk.metadata.get("rule_type") in allowed]
        return result

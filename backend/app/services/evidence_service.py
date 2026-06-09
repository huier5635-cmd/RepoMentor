from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from app.core.schemas import EvidenceItem, SourceType


class EvidenceService:
    def make(
        self,
        source_type: SourceType,
        source_ref: str,
        quote: str,
        supports_claim: str,
        file_path: str = "",
        issue_number: int | None = None,
        line_start: int | None = None,
        line_end: int | None = None,
        confidence: float = 1.0,
    ) -> EvidenceItem:
        key = f"{source_type}:{source_ref}:{file_path}:{issue_number}:{line_start}:{quote[:80]}"
        return EvidenceItem(
            evidence_id=str(uuid5(NAMESPACE_URL, key)),
            source_type=source_type,
            source_ref=source_ref,
            source_path=file_path or source_ref,
            title=source_ref,
            file_path=file_path,
            issue_number=issue_number,
            line_start=line_start,
            line_end=line_end,
            quote=quote[:600],
            snippet=quote[:600],
            supports_claim=supports_claim,
            reason=supports_claim,
            confidence=confidence,
        )

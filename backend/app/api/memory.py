from __future__ import annotations

from fastapi import APIRouter

from app.core.orchestrator import orchestrator


router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/{session_id}")
def get_memory(session_id: str) -> dict[str, object]:
    return orchestrator.get_trace(session_id)

from __future__ import annotations

from fastapi import APIRouter

from app.core.orchestrator_provider import get_graph_status


router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/status")
def get_status() -> dict[str, object]:
    return get_graph_status()

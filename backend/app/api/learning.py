from __future__ import annotations

from fastapi import APIRouter

from app.core.orchestrator import orchestrator
from app.core.schemas import LearningPathResponse


router = APIRouter(prefix="/repos", tags=["learning"])


@router.get("/{repo_id}/learning-path", response_model=LearningPathResponse)
def learning_path(repo_id: str) -> LearningPathResponse:
    return orchestrator.generate_learning_path(repo_id)

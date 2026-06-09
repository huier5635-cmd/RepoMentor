from __future__ import annotations

from fastapi import APIRouter

from app.core.orchestrator_provider import get_active_orchestrator
from app.core.schemas import FinalAnswer, QARequest


router = APIRouter(prefix="/repos", tags=["qa"])


@router.post("/{repo_id}/qa", response_model=FinalAnswer)
def answer_question(repo_id: str, request: QARequest) -> FinalAnswer:
    return get_active_orchestrator().answer_question(repo_id, request.question)

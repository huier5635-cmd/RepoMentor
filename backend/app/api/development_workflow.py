from __future__ import annotations

from fastapi import APIRouter

from app.core.orchestrator import orchestrator
from app.core.schemas import DevelopmentWorkflowResponse


router = APIRouter(prefix="/repos", tags=["development-workflow"])


@router.get("/{repo_id}/development-workflow", response_model=DevelopmentWorkflowResponse)
def get_development_workflow(repo_id: str) -> DevelopmentWorkflowResponse:
    return orchestrator.get_development_workflow(repo_id)

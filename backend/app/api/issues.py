from __future__ import annotations

from fastapi import APIRouter

from app.core.orchestrator_provider import get_active_orchestrator
from app.core.schemas import IssueRecommendationResponse
from app.services.learning_agent_service import LearningAgentService


router = APIRouter(prefix="/repos", tags=["issues"])


@router.get("/{repo_id}/issues/recommend", response_model=IssueRecommendationResponse)
def recommend_issues(repo_id: str) -> IssueRecommendationResponse:
    return LearningAgentService(get_active_orchestrator().repo_store).contribution_funnel(repo_id)

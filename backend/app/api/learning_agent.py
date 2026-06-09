from __future__ import annotations

from fastapi import APIRouter

from app.core.orchestrator_provider import get_active_orchestrator
from app.core.schemas import (
    ArchitectureTour,
    BilingualDocView,
    ChangeImpactRequest,
    ChangeImpactResponse,
    IssueRecommendationResponse,
    LearningAgentDebugBundle,
    LearningCheckRequest,
    LearningCheckResponse,
    LearningPathV2Response,
    ModuleStudyCard,
    OnboardingDebtReport,
    ProjectGlossary,
    TutorialDraft,
)
from app.services.learning_agent_service import LearningAgentService


router = APIRouter(prefix="/repos", tags=["learning-agent"])


def service() -> LearningAgentService:
    return LearningAgentService(get_active_orchestrator().repo_store)


@router.get("/{repo_id}/learning-path-v2", response_model=LearningPathV2Response)
def learning_path_v2(repo_id: str) -> LearningPathV2Response:
    return service().learning_path_v2(repo_id)


@router.get("/{repo_id}/architecture-tour", response_model=ArchitectureTour)
def architecture_tour(repo_id: str, audience: str = "newcomer") -> ArchitectureTour:
    return service().architecture_tour(repo_id, audience=audience)


@router.get("/{repo_id}/module-study-cards", response_model=list[ModuleStudyCard])
def module_study_cards(repo_id: str, audience: str = "newcomer", limit: int = 8) -> list[ModuleStudyCard]:
    return service().module_study_cards(repo_id, audience=audience, limit=limit)


@router.get("/{repo_id}/glossary", response_model=ProjectGlossary)
def glossary(repo_id: str) -> ProjectGlossary:
    return service().glossary(repo_id)


@router.get("/{repo_id}/bilingual-docs", response_model=BilingualDocView)
def bilingual_docs(repo_id: str, source_path: str = "") -> BilingualDocView:
    return service().bilingual_doc_view(repo_id, source_path=source_path)


@router.post("/{repo_id}/learning-check", response_model=LearningCheckResponse)
def learning_check(repo_id: str, request: LearningCheckRequest) -> LearningCheckResponse:
    return service().learning_check(repo_id, request)


@router.post("/{repo_id}/change-impact", response_model=ChangeImpactResponse)
def change_impact(repo_id: str, request: ChangeImpactRequest) -> ChangeImpactResponse:
    return service().change_impact(repo_id, request)


@router.get("/{repo_id}/contribution-funnel", response_model=IssueRecommendationResponse)
def contribution_funnel(repo_id: str) -> IssueRecommendationResponse:
    return service().contribution_funnel(repo_id)


@router.get("/{repo_id}/onboarding-debt", response_model=OnboardingDebtReport)
def onboarding_debt(repo_id: str) -> OnboardingDebtReport:
    return service().onboarding_debt(repo_id)


@router.get("/{repo_id}/tutorials", response_model=list[TutorialDraft])
def tutorials(repo_id: str) -> list[TutorialDraft]:
    return service().tutorials(repo_id)


@router.get("/{repo_id}/learning-agent/debug-bundle", response_model=LearningAgentDebugBundle)
def learning_agent_debug_bundle(repo_id: str) -> LearningAgentDebugBundle:
    return service().debug_bundle(repo_id)

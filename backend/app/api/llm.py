from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.orchestrator import orchestrator


router = APIRouter(prefix="/llm", tags=["llm"])


class LLMConfigureRequest(BaseModel):
    provider: str = Field(default="mock")
    deepseek_api_key: str = Field(default="")
    deepseek_model: str = Field(default="deepseek-chat")
    deepseek_base_url: str = Field(default="https://api.deepseek.com")
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="")
    openai_base_url: str = Field(default="https://api.openai.com/v1")


@router.get("/status")
def get_llm_status() -> dict[str, object]:
    return orchestrator.get_llm_status()


@router.post("/configure")
def configure_llm(request: LLMConfigureRequest) -> dict[str, object]:
    return orchestrator.configure_llm(request.model_dump())

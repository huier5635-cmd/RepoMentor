from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.orchestrator import orchestrator


router = APIRouter(prefix="/model", tags=["model"])


class ModelConfigRequest(BaseModel):
    provider: str = Field(default="mock")
    model: str = Field(default="")
    base_url: str = Field(default="")
    api_key: str = Field(default="")
    persist: bool = Field(default=False)


@router.get("/status")
def get_model_status() -> dict[str, object]:
    return orchestrator.get_model_status()


@router.post("/config")
def configure_model(request: ModelConfigRequest) -> dict[str, object]:
    return orchestrator.configure_model(request.model_dump())


@router.post("/test")
def test_model_connection() -> dict[str, object]:
    return orchestrator.test_model_connection()

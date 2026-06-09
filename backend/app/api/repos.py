from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.orchestrator_provider import get_active_orchestrator
from app.core.schemas import AnalyzeRepoRequest, AnalyzeRepoResponse


router = APIRouter(prefix="/repos", tags=["repos"])


@router.post("/analyze", response_model=AnalyzeRepoResponse)
def analyze_repo(request: AnalyzeRepoRequest) -> AnalyzeRepoResponse:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(get_active_orchestrator().analyze_repo, request.repo_url)
    try:
        return future.result(timeout=get_settings().analyze_timeout_seconds)
    except TimeoutError as error:
        future.cancel()
        raise HTTPException(status_code=408, detail="仓库分析超时，请换用更小的仓库或稍后重试。") from error
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


@router.get("/{repo_id}/graph")
def get_repo_graph(repo_id: str) -> JSONResponse:
    graph = get_active_orchestrator().get_graph(repo_id)
    return JSONResponse(content=jsonable_encoder(graph))

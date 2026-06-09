from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import debug, development_workflow, graph, issues, learning, learning_agent, llm, memory, model, qa, repos
from app.core.config import get_settings


settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repos.router, prefix="/api")
app.include_router(debug.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(qa.router, prefix="/api")
app.include_router(learning.router, prefix="/api")
app.include_router(learning_agent.router, prefix="/api")
app.include_router(issues.router, prefix="/api")
app.include_router(development_workflow.router, prefix="/api")
app.include_router(llm.router, prefix="/api")
app.include_router(model.router, prefix="/api")
app.include_router(memory.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

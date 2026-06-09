from __future__ import annotations

from app.core.config import get_settings
from app.core.orchestrator import orchestrator as legacy_orchestrator
from app.graphs.graph_orchestrator import GraphOrchestrator


graph_orchestrator = GraphOrchestrator(legacy_orchestrator)


def get_legacy_orchestrator():
    return legacy_orchestrator


def get_graph_orchestrator() -> GraphOrchestrator:
    return graph_orchestrator


def get_active_orchestrator():
    return graph_orchestrator if get_settings().langgraph_enabled else legacy_orchestrator


def get_graph_status() -> dict[str, object]:
    return graph_orchestrator.graph_status()

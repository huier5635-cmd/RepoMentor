from __future__ import annotations

from typing import Any


def thread_id_for_analyze(repo_id_or_hash: str) -> str:
    return f"analyze:{repo_id_or_hash}"


def thread_id_for_qa(repo_id: str, session_id: str) -> str:
    return f"qa:{repo_id}:{session_id}"


def summarize_dict(value: dict[str, Any] | None, max_items: int = 8) -> str:
    if not value:
        return ""
    parts = []
    for index, (key, item) in enumerate(value.items()):
        if index >= max_items:
            break
        parts.append(f"{key}={_short(item)}")
    return "; ".join(parts)


def graph_status_payload(enabled: bool, active: str, backend: str, available: bool, warning: str = "") -> dict[str, Any]:
    return {
        "langgraph_enabled": enabled,
        "checkpoint_backend": backend,
        "checkpoint_available": available,
        "active_orchestrator": active,
        "warning": warning,
    }


def _short(value: Any) -> str:
    text = str(value)
    return text if len(text) <= 80 else text[:77] + "..."


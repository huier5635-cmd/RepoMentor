from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


TraceEventType = Literal["start", "success", "error", "decision", "retry", "fallback", "checkpoint"]


class TraceEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    thread_id: str
    graph_name: str
    node_name: str
    event_type: TraceEventType
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    elapsed_ms: int | None = None
    input_summary: str = ""
    output_summary: str = ""
    error: str = ""
    state_keys_changed: list[str] = Field(default_factory=list)
    evidence_count: int = 0
    model_info: dict[str, Any] | None = None


class GraphTraceStore:
    def __init__(self) -> None:
        self._traces: dict[str, list[dict[str, Any]]] = {}

    def append(self, thread_id: str, event: TraceEvent | dict[str, Any]) -> None:
        payload = event.model_dump(mode="json") if isinstance(event, TraceEvent) else dict(event)
        self._traces.setdefault(thread_id, []).append(payload)

    def get(self, thread_id: str) -> list[dict[str, Any]]:
        return list(self._traces.get(thread_id, []))

    def clear(self, thread_id: str) -> None:
        self._traces.pop(thread_id, None)


graph_trace_store = GraphTraceStore()


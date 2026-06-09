from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import get_settings


@dataclass
class CheckpointerInfo:
    saver: Any
    backend: str
    available: bool
    warning: str = ""


class InMemoryCheckpointer:
    def __init__(self) -> None:
        self._states: dict[str, dict[str, Any]] = {}

    def put_state(self, thread_id: str, state: dict[str, Any]) -> None:
        self._states[thread_id] = dict(state)

    def get_state(self, thread_id: str) -> dict[str, Any] | None:
        state = self._states.get(thread_id)
        return dict(state) if state else None


class SQLiteCheckpointer:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS graph_checkpoints "
                "(thread_id TEXT PRIMARY KEY, state_json TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"
            )

    def put_state(self, thread_id: str, state: dict[str, Any]) -> None:
        payload = json.dumps(state, ensure_ascii=False, default=str)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO graph_checkpoints(thread_id, state_json, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(thread_id) DO UPDATE SET state_json = excluded.state_json, updated_at = CURRENT_TIMESTAMP",
                (thread_id, payload),
            )

    def get_state(self, thread_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT state_json FROM graph_checkpoints WHERE thread_id = ?", (thread_id,)).fetchone()
        return json.loads(row[0]) if row else None


memory_checkpointer = InMemoryCheckpointer()


def get_checkpointer() -> CheckpointerInfo:
    settings = get_settings()
    backend = (settings.langgraph_checkpoint_backend or "memory").lower()
    if backend == "sqlite":
        try:
            return CheckpointerInfo(saver=SQLiteCheckpointer(settings.langgraph_sqlite_path), backend="sqlite", available=True)
        except Exception as error:
            return CheckpointerInfo(
                saver=memory_checkpointer,
                backend="memory",
                available=True,
                warning=f"sqlite checkpointer unavailable; using memory: {type(error).__name__}",
            )
    if backend == "memory":
        try:
            from langgraph.checkpoint.memory import MemorySaver  # type: ignore  # noqa: F401

            return CheckpointerInfo(saver=memory_checkpointer, backend="memory", available=True)
        except Exception as error:
            return CheckpointerInfo(
                saver=memory_checkpointer,
                backend="memory",
                available=True,
                warning=f"LangGraph MemorySaver unavailable; using local memory: {type(error).__name__}",
            )
    return CheckpointerInfo(
        saver=memory_checkpointer,
        backend="memory",
        available=True,
        warning=f"unsupported checkpoint backend {backend}; using memory",
    )


def checkpoint_config(thread_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": thread_id}}

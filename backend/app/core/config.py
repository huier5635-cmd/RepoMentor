from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except Exception:
    pass


class Settings(BaseModel):
    app_name: str = "RepoMentor"
    cache_dir: Path = Path(".repomentor_cache")
    repo_cache_dir: Path = Path(".repomentor_cache/repos")
    record_cache_dir: Path = Path(".repomentor_cache/records")
    github_token_env: str = "GITHUB_TOKEN"
    backend_cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    max_repo_files: int = 1000
    max_file_size_bytes: int = 300_000
    max_preview_chars: int = 1_200
    analyze_timeout_seconds: int = 120
    enable_public_demo_guard: bool = False
    langgraph_enabled: bool = False
    langgraph_checkpoint_backend: str = "memory"
    langgraph_sqlite_path: Path = Path(".repomentor_cache/langgraph_checkpoints.sqlite")
    langgraph_trace_enabled: bool = True
    langgraph_max_retries: int = 2


@lru_cache
def get_settings() -> Settings:
    cache_dir = Path(os.getenv("REPOMENTOR_CACHE_DIR", ".repomentor_cache"))
    max_file_size_kb = _env_int("MAX_FILE_SIZE_KB", 512)
    settings = Settings(
        cache_dir=cache_dir,
        repo_cache_dir=cache_dir / "repos",
        record_cache_dir=cache_dir / "records",
        backend_cors_origins=_env_list(
            "BACKEND_CORS_ORIGINS",
            ["http://localhost:5173", "http://127.0.0.1:5173"],
        ),
        max_repo_files=_env_int("MAX_REPO_FILES", 1000),
        max_file_size_bytes=max_file_size_kb * 1024,
        analyze_timeout_seconds=_env_int("ANALYZE_TIMEOUT_SECONDS", 120),
        enable_public_demo_guard=_env_bool("ENABLE_PUBLIC_DEMO_GUARD", False),
        langgraph_enabled=_env_bool("LANGGRAPH_ENABLED", False),
        langgraph_checkpoint_backend=os.getenv("LANGGRAPH_CHECKPOINT_BACKEND", "memory"),
        langgraph_sqlite_path=Path(os.getenv("LANGGRAPH_SQLITE_PATH", ".repomentor_cache/langgraph_checkpoints.sqlite")),
        langgraph_trace_enabled=_env_bool("LANGGRAPH_TRACE_ENABLED", True),
        langgraph_max_retries=int(os.getenv("LANGGRAPH_MAX_RETRIES", "2") or "2"),
    )
    settings.repo_cache_dir.mkdir(parents=True, exist_ok=True)
    settings.record_cache_dir.mkdir(parents=True, exist_ok=True)
    settings.langgraph_sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return settings


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    cleaned = raw.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    values = [item.strip().strip("'\"") for item in cleaned.split(",")]
    return [item for item in values if item]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

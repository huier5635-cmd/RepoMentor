from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.core.schemas import RepositoryRecord


class RepositoryStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._records: dict[str, RepositoryRecord] = {}

    def save(self, record: RepositoryRecord) -> None:
        self._records[record.repo_id] = record
        path = self._path(record.repo_id)
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    def load(self, repo_id: str) -> RepositoryRecord:
        if repo_id in self._records:
            return self._records[repo_id]
        path = self._path(repo_id)
        if not path.exists():
            raise KeyError(f"unknown repo_id: {repo_id}")
        record = RepositoryRecord.model_validate_json(path.read_text(encoding="utf-8"))
        self._records[repo_id] = record
        return record

    def _path(self, repo_id: str) -> Path:
        return self.settings.record_cache_dir / f"{repo_id}.json"

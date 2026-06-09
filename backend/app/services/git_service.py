from __future__ import annotations

import hashlib
import re
import subprocess
from subprocess import CalledProcessError
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings


@dataclass(frozen=True)
class PreparedRepository:
    repo_id: str
    repo_url: str
    local_path: str
    owner: str
    name: str
    default_branch: str


class GitService:
    def prepare_repository(self, repo_url: str) -> PreparedRepository:
        repo_url = (repo_url or "").strip()
        if not repo_url:
            raise ValueError("repo_url must be a non-empty existing local path or a GitHub repository URL")
        settings = get_settings()
        repo_id = hashlib.sha1(repo_url.encode("utf-8")).hexdigest()[:12]
        owner, name = self.parse_owner_name(repo_url)
        local_path = settings.repo_cache_dir / f"{owner or 'local'}-{name or repo_id}-{repo_id}"
        if self._is_local_path(repo_url):
            source = Path(repo_url).expanduser().resolve()
            return PreparedRepository(
                repo_id=repo_id,
                repo_url=str(source),
                local_path=str(source),
                owner=owner,
                name=name or source.name,
                default_branch=self.default_branch(source),
            )
        if not owner or not name:
            raise ValueError("repo_url must be an existing local path or a GitHub repository URL")
        if not local_path.exists():
            try:
                subprocess.run(["git", "clone", "--depth", "1", repo_url, str(local_path)], check=True, capture_output=True, text=True)
            except CalledProcessError as error:
                message = error.stderr or error.stdout or str(error)
                raise RuntimeError(f"git clone failed: {message.strip()}") from error
        else:
            subprocess.run(["git", "-C", str(local_path), "fetch", "--depth", "1"], check=False, capture_output=True, text=True)
        return PreparedRepository(
            repo_id=repo_id,
            repo_url=repo_url,
            local_path=str(local_path),
            owner=owner,
            name=name,
            default_branch=self.default_branch(local_path),
        )

    def parse_owner_name(self, repo_url: str) -> tuple[str, str]:
        repo_url = (repo_url or "").strip()
        if not repo_url:
            return "", ""
        match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<name>[^/.]+)", repo_url)
        if match:
            return match.group("owner"), match.group("name").removesuffix(".git")
        path = Path(repo_url)
        return "", path.name if path.exists() else ""

    def default_branch(self, local_path: Path) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(local_path), "branch", "--show-current"],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip() or "main"
        except Exception:
            return "main"

    def _is_local_path(self, repo_url: str) -> bool:
        repo_url = (repo_url or "").strip()
        if not repo_url:
            return False
        return Path(repo_url).expanduser().exists()

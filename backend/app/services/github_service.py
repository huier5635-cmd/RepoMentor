from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from app.core.config import get_settings
from app.core.schemas import IssueCard


class GitHubService:
    def fetch_open_issues(self, owner: str, name: str, limit: int = 30) -> list[IssueCard]:
        if not owner or not name:
            return []
        settings = get_settings()
        query = urllib.parse.urlencode({"state": "open", "per_page": min(limit, 100)})
        url = f"https://api.github.com/repos/{owner}/{name}/issues?{query}"
        headers = {"Accept": "application/vnd.github+json"}
        token = os.getenv(settings.github_token_env)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []
        cards: list[IssueCard] = []
        for item in payload:
            if "pull_request" in item:
                continue
            labels = [label.get("name", "") for label in item.get("labels", []) if label.get("name")]
            issue_type = self._classify_issue(item.get("title", ""), item.get("body") or "", labels)
            cards.append(
                IssueCard(
                    issue_number=item.get("number", 0),
                    title=item.get("title", ""),
                    body=item.get("body") or "",
                    labels=labels,
                    comments_count=item.get("comments", 0),
                    created_at=item.get("created_at", ""),
                    updated_at=item.get("updated_at", ""),
                    author_association=item.get("author_association", ""),
                    issue_type=issue_type,
                    url=item.get("html_url", ""),
                    difficulty=self._difficulty(issue_type, labels, item.get("body") or ""),
                    skill_tags=self._skill_tags(issue_type, labels, item.get("body") or ""),
                )
            )
        return cards

    def _classify_issue(self, title: str, body: str, labels: list[str]) -> str:
        text = " ".join([title, body, *labels]).lower()
        if "good first" in text:
            return "good_first_issue"
        if "help wanted" in text:
            return "help_wanted"
        if "bug" in text or "error" in text:
            return "bug"
        if "doc" in text or "readme" in text:
            return "docs"
        if "test" in text:
            return "test"
        if "feature" in text or "enhancement" in text:
            return "feature"
        return "unknown"

    def _difficulty(self, issue_type: str, labels: list[str], body: str) -> str:
        text = " ".join(labels).lower()
        if issue_type in {"docs", "test", "good_first_issue"} or "easy" in text:
            return "easy"
        if len(body) > 1200 or issue_type == "feature":
            return "medium"
        return "unknown"

    def _skill_tags(self, issue_type: str, labels: list[str], body: str) -> list[str]:
        text = " ".join([issue_type, body, *labels]).lower()
        tags: set[str] = set()
        for tag in ["docs", "test", "python", "javascript", "typescript", "api", "frontend", "backend"]:
            if tag in text:
                tags.add(tag)
        if issue_type in {"docs", "test"}:
            tags.add(issue_type)
        return sorted(tags)

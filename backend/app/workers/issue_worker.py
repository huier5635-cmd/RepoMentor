from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from app.core.schemas import ChunkDoc, IssueWorkerInput, IssueWorkerResult, SourceType, WorkerOutput, WorkerStatus
from app.services.evidence_service import EvidenceService
from app.services.github_service import GitHubService
from app.workers.base_worker import BaseWorker


class IssueWorker(BaseWorker[IssueWorkerInput, IssueWorkerResult]):
    worker_name = "Issue Worker"

    def __init__(self) -> None:
        self.github = GitHubService()
        self.evidence = EvidenceService()

    def run(self, worker_input: IssueWorkerInput) -> IssueWorkerResult:
        issues = self.github.fetch_open_issues(worker_input.owner, worker_input.name)
        for issue in issues:
            issue.recommendation_score = self._score_issue(issue.labels, issue.comments_count, issue.body, issue.issue_type)
        issues = sorted(issues, key=lambda item: item.recommendation_score, reverse=True)
        chunks = [
            ChunkDoc(
                chunk_id=str(uuid5(NAMESPACE_URL, f"issue:{issue.issue_number}:{issue.title}")),
                source_type=SourceType.ISSUE,
                issue_number=issue.issue_number,
                title=issue.title,
                text="\n".join([issue.title, issue.body])[:1600],
                metadata={
                    "labels": issue.labels,
                    "issue_type": issue.issue_type,
                    "difficulty": issue.difficulty,
                    "skill_tags": issue.skill_tags,
                },
            )
            for issue in issues
        ]
        output = WorkerOutput(
            worker_name=self.worker_name,
            task="fetch GitHub open issues and produce recommendation candidates",
            status=WorkerStatus.SUCCESS if issues else WorkerStatus.PARTIAL,
            findings=[f"fetched {len(issues)} open non-PR issues"],
            evidence=[
                self.evidence.make(
                    SourceType.ISSUES,
                    f"issue #{issue.issue_number}",
                    issue.title,
                    "real GitHub issue used as recommendation evidence",
                    issue_number=issue.issue_number,
                    confidence=0.95,
                )
                for issue in issues[:8]
            ],
            uncertainties=[] if issues else ["no open issues fetched; repository may have no issues or GitHub API was unavailable"],
            next_actions=["combine labels, activity, scope, tests, docs and skill tags for recommendations"],
        )
        return IssueWorkerResult(issues=issues, chunks=chunks, worker_output=output)

    def _score_issue(self, labels: list[str], comments_count: int, body: str, issue_type: str) -> float:
        label_text = " ".join(labels).lower()
        score = 0.0
        if "good first" in label_text:
            score += 2.0
        if "help wanted" in label_text:
            score += 1.5
        if issue_type in {"docs", "test"}:
            score += 1.3
        if len(body) < 1500:
            score += 0.8
        if comments_count <= 5:
            score += 0.5
        return score

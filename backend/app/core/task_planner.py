from __future__ import annotations

from app.core.schemas import TaskType


class TaskPlanner:
    def plan(self, task_type: TaskType) -> list[str]:
        base = ["hybrid_retrieval"]
        if task_type == TaskType.CODE_EXPLANATION:
            return ["code_explanation_worker", *base]
        if task_type == TaskType.TEST_MAPPING:
            return ["test_worker_lookup", *base]
        if task_type == TaskType.ISSUE_RECOMMENDATION:
            return ["issue_worker_lookup", *base]
        if task_type == TaskType.DEVELOPMENT_WORKFLOW:
            return ["docs_worker_lookup", "development_workflow_worker", "issue_worker_lookup", "test_worker_lookup", *base]
        return base

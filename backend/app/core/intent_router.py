from __future__ import annotations

from app.core.schemas import TaskType


class IntentRouter:
    def classify(self, question: str) -> TaskType:
        text = (question or "").lower()

        if self._contains_any(text, ["哪些测试", "测试映射", "test mapping", "改动后跑哪些"]):
            return TaskType.TEST_MAPPING

        if self._contains_any(
            text,
            [
                "怎么启动",
                "如何启动",
                "怎么安装",
                "如何安装",
                "怎么运行",
                "如何运行",
                "启动",
                "安装",
                "运行",
                "测试命令",
                "怎么跑测试",
                "run",
                "setup",
                "install",
                "quick start",
                "quickstart",
            ],
        ):
            return TaskType.SETUP_RUN

        if self._contains_any(
            text,
            [
                "参与贡献",
                "开始贡献",
                "开发流程",
                "代码规范",
                "贡献流程",
                "pr",
                "pull request",
                "分支",
                "branch",
                "提交信息",
                "commit",
                "ci",
                "lint",
                "format",
                "检查什么",
                "做哪些检查",
                "contribute",
                "contributing",
                "workflow",
            ],
        ):
            return TaskType.DEVELOPMENT_WORKFLOW

        if self._contains_any(text, ["从哪里", "学习", "入门", "路径", "learn", "start"]):
            return TaskType.LEARNING_PATH

        if self._contains_any(text, ["issue", "任务", "贡献", "good first", "推荐"]):
            return TaskType.ISSUE_RECOMMENDATION

        if self._contains_any(text, ["函数", "模块", "class", "function", "怎么工作", "explain"]):
            return TaskType.CODE_EXPLANATION

        if self._contains_any(text, ["做什么", "是什么", "overview", "about"]):
            return TaskType.REPO_OVERVIEW

        return TaskType.GENERAL_QA

    def _contains_any(self, text: str, keywords: list[str]) -> bool:
        return any(keyword in text for keyword in keywords)

from __future__ import annotations

from collections import Counter
from pathlib import Path

from app.core.schemas import (
    ConfidenceLevel,
    EvidenceItem,
    FileNode,
    FileType,
    GraphEdge,
    QualityCommand,
    RepositoryIntelligenceGraph,
    SourceType,
    TaskType,
    WorkerOutput,
)
from app.services.evidence_service import EvidenceService


class EvidenceBuilder:
    def __init__(self) -> None:
        self.evidence = EvidenceService()

    def build_for_task(
        self,
        task_type: TaskType,
        question: str,
        repo_graph: RepositoryIntelligenceGraph,
        worker_outputs: list[WorkerOutput] | None = None,
    ) -> list[EvidenceItem]:
        question = question or ""
        worker_outputs = worker_outputs or []
        if self._is_entrypoint_question(question):
            return self.build_entrypoints_evidence(repo_graph)
        if self._is_core_modules_question(question):
            return self.build_core_modules_evidence(repo_graph, repo_graph.symbols)
        if self._is_docs_question(question):
            return self.build_docs_recommendation_evidence(worker_outputs, repo_graph)
        if self._is_beginner_task_question(question):
            return self.build_issue_or_internal_task_evidence(worker_outputs, repo_graph)
        if task_type == TaskType.LEARNING_PATH:
            return self.build_learning_path_evidence(repo_graph, worker_outputs)
        if task_type == TaskType.DEVELOPMENT_WORKFLOW:
            return self.build_development_workflow_evidence(worker_outputs, repo_graph)
        if task_type == TaskType.SETUP_RUN:
            return self.build_setup_evidence(repo_graph, worker_outputs)
        if task_type == TaskType.ISSUE_RECOMMENDATION:
            return self.build_issue_or_internal_task_evidence(worker_outputs, repo_graph)
        if task_type == TaskType.CODE_EXPLANATION:
            return self.build_core_modules_evidence(repo_graph, repo_graph.symbols)
        return self.build_repo_overview_evidence(repo_graph, worker_outputs)

    def build_repo_overview_evidence(
        self,
        repo_graph: RepositoryIntelligenceGraph,
        worker_outputs: list[WorkerOutput] | None = None,
    ) -> list[EvidenceItem]:
        values = self._readme_evidence(repo_graph)
        if not values:
            docs = self._doc_files(repo_graph)
            values.extend(self._file_evidence(file, SourceType.DOCS, "文档文件可用于判断仓库用途") for file in docs[:3])
        if not values:
            values.append(
                self._make(
                    SourceType.GRAPH,
                    "RepositoryGraph summary",
                    self._graph_summary_quote(repo_graph),
                    "README 缺失时，用仓库图谱摘要提供中低置信概览证据",
                    confidence=0.55 if repo_graph.files else 0.2,
                )
            )
        if worker_outputs:
            values.extend(self._worker_evidence(worker_outputs, "Docs Worker")[:2])
        return self._dedupe(values)

    def build_core_modules_evidence(
        self,
        repo_graph: RepositoryIntelligenceGraph,
        symbols,
    ) -> list[EvidenceItem]:
        values: list[EvidenceItem] = []
        symbol_counts = Counter(symbol.file_path for symbol in symbols)
        source_files = [file for file in repo_graph.files if self._is_source_file(file)]
        for directory in repo_graph.core_directories[:6]:
            files_in_dir = [file for file in source_files if file.path == directory or file.path.startswith(f"{directory}/")]
            symbol_count = sum(symbol_counts.get(file.path, 0) for file in files_in_dir)
            values.append(
                self._make(
                    SourceType.GRAPH,
                    f"core directory: {directory}",
                    f"{directory} 包含 {len(files_in_dir)} 个源码文件、{symbol_count} 个符号。",
                    "核心目录来自 RepositoryGraph 的目录和符号统计",
                    file_path=directory,
                    confidence=0.78 if files_in_dir else 0.55,
                )
            )
        for file_path, count in symbol_counts.most_common(6):
            file = self._file_by_path(repo_graph, file_path)
            if not file:
                continue
            values.append(
                self._make(
                    SourceType.CODE,
                    file.path,
                    f"{file.path} 定义了 {count} 个已解析符号。",
                    "核心源码文件来自 symbols summary",
                    file_path=file.path,
                    confidence=0.82,
                )
            )
        for entrypoint in repo_graph.entrypoints[:3]:
            values.append(
                self._make(
                    SourceType.CODE,
                    entrypoint.path,
                    f"{entrypoint.path}: {entrypoint.reason}",
                    "入口文件也是核心阅读路径的一部分",
                    file_path=entrypoint.path,
                    confidence=self._confidence_value(entrypoint.confidence),
                )
            )
        return self._dedupe(values)

    def build_entrypoints_evidence(self, repo_graph: RepositoryIntelligenceGraph) -> list[EvidenceItem]:
        values: list[EvidenceItem] = []
        for entrypoint in repo_graph.entrypoints:
            source_type = SourceType.CODE if self._file_by_path(repo_graph, entrypoint.path) else SourceType.GRAPH
            values.append(
                self._make(
                    source_type,
                    entrypoint.path,
                    f"{entrypoint.path}；原因：{entrypoint.reason}；来源：{entrypoint.source}；置信度：{entrypoint.confidence.value}",
                    "入口文件来自 RepositoryGraph entrypoints",
                    file_path=entrypoint.path if source_type == SourceType.CODE else "",
                    confidence=self._confidence_value(entrypoint.confidence),
                )
            )
        if not values:
            values.append(
                self._make(
                    SourceType.GRAPH,
                    "RepositoryGraph entrypoints",
                    "RepositoryGraph 未检测到明确入口文件。",
                    "入口文件缺失是结构化不确定性，不是模型推测",
                    confidence=0.35,
                )
            )
        return self._dedupe(values)

    def build_docs_recommendation_evidence(
        self,
        docs_worker_output: list[WorkerOutput] | WorkerOutput | None,
        repo_graph: RepositoryIntelligenceGraph | None = None,
    ) -> list[EvidenceItem]:
        values: list[EvidenceItem] = []
        if repo_graph:
            values.extend(self._readme_evidence(repo_graph))
            preferred = [
                "docs/architecture.md",
                "docs/academic_evaluation.md",
                "docs/memory_eval.md",
                "docs/reproducibility_checklist.md",
                "docs/stress_test_report.md",
            ]
            by_path = {file.path.lower(): file for file in self._doc_files(repo_graph)}
            for path in preferred:
                file = by_path.get(path.lower())
                if file:
                    values.append(self._file_evidence(file, SourceType.DOCS, "文档推荐来自 README/docs 文件结构"))
            for file in self._doc_files(repo_graph):
                if len(values) >= 8:
                    break
                values.append(self._file_evidence(file, SourceType.DOCS, "文档推荐来自 docs 目录"))
        if isinstance(docs_worker_output, WorkerOutput):
            values.extend(docs_worker_output.evidence)
        elif docs_worker_output:
            values.extend(self._worker_evidence(docs_worker_output, "Docs Worker")[:6])
        return self._dedupe(values)

    def build_learning_path_evidence(
        self,
        repo_graph: RepositoryIntelligenceGraph,
        worker_outputs: list[WorkerOutput] | None = None,
    ) -> list[EvidenceItem]:
        values: list[EvidenceItem] = []
        values.extend(self._readme_evidence(repo_graph)[:2])
        values.extend(self._command_evidence(repo_graph)[:4])
        values.extend(self.build_core_modules_evidence(repo_graph, repo_graph.symbols)[:4])
        values.extend(self.build_entrypoints_evidence(repo_graph)[:3])
        values.extend(self._test_evidence(repo_graph)[:4])
        values.extend(self.build_development_workflow_evidence(worker_outputs or [], repo_graph)[:4])
        values.extend(self.build_issue_or_internal_task_evidence(worker_outputs or [], repo_graph)[:3])
        return self._dedupe(values)

    def build_issue_or_internal_task_evidence(
        self,
        issue_worker_output: list[WorkerOutput] | WorkerOutput | None,
        repo_graph: RepositoryIntelligenceGraph,
    ) -> list[EvidenceItem]:
        values: list[EvidenceItem] = []
        outputs: list[WorkerOutput] = []
        if isinstance(issue_worker_output, WorkerOutput):
            outputs = [issue_worker_output]
        elif issue_worker_output:
            outputs = issue_worker_output
        values.extend(self._worker_evidence(outputs, "Issue Worker"))
        if values:
            return self._dedupe(values)

        for item in self._readme_evidence(repo_graph)[:1]:
            values.append(
                self._make(
                    SourceType.INTERNAL_SUGGESTION,
                    item.source_ref,
                    item.quote,
                    "open issues 为 0 时，README 可支持 internal first task",
                    file_path=item.file_path,
                    confidence=0.62,
                )
            )
        for item in self._test_evidence(repo_graph)[:2]:
            values.append(
                self._make(
                    SourceType.INTERNAL_SUGGESTION,
                    item.source_ref,
                    item.quote,
                    "open issues 为 0 时，测试文件/命令可支持 internal first task",
                    file_path=item.file_path,
                    confidence=0.6,
                )
            )
        for item in self.build_entrypoints_evidence(repo_graph)[:2]:
            values.append(
                self._make(
                    SourceType.INTERNAL_SUGGESTION,
                    item.source_ref,
                    item.quote,
                    "open issues 为 0 时，入口文件可支持 internal first task",
                    file_path=item.file_path,
                    confidence=min(item.confidence, 0.62),
                )
            )
        if not values:
            values.append(
                self._make(
                    SourceType.INTERNAL_SUGGESTION,
                    "RepositoryGraph summary",
                    self._graph_summary_quote(repo_graph),
                    "open issues 为 0 时，用仓库结构生成 internal first task",
                    confidence=0.48,
                )
            )
        return self._dedupe(values)

    def build_development_workflow_evidence(
        self,
        workflow_worker_output: list[WorkerOutput] | WorkerOutput | None,
        repo_graph: RepositoryIntelligenceGraph | None = None,
    ) -> list[EvidenceItem]:
        values: list[EvidenceItem] = []
        if repo_graph and repo_graph.development_workflow:
            guide = repo_graph.development_workflow
            values.extend(guide.evidence)
            values.extend(self._quality_command_evidence(guide.quality_commands[:8]))
            if guide.uncertainties:
                values.append(
                    self._make(
                        SourceType.WORKFLOW,
                        "DevelopmentWorkflowWorker uncertainties",
                        "；".join(self._dedupe_strings(guide.uncertainties)[:6]),
                        "缺失 CONTRIBUTING、CI、lint、format 等是 workflow uncertainty",
                        confidence=0.72,
                    )
                )
        if isinstance(workflow_worker_output, WorkerOutput):
            values.extend(workflow_worker_output.evidence)
        elif workflow_worker_output:
            values.extend(self._worker_evidence(workflow_worker_output, "Development Workflow Worker"))
        return self._dedupe(values)

    def build_setup_evidence(
        self,
        repo_graph: RepositoryIntelligenceGraph,
        worker_outputs: list[WorkerOutput] | None = None,
    ) -> list[EvidenceItem]:
        values: list[EvidenceItem] = []
        values.extend(self._readme_evidence(repo_graph)[:3])
        values.extend(self._command_evidence(repo_graph))
        values.extend(self.build_development_workflow_evidence(worker_outputs or [], repo_graph)[:5])
        return self._dedupe(values)

    def _readme_evidence(self, graph: RepositoryIntelligenceGraph) -> list[EvidenceItem]:
        readmes = [
            file
            for file in graph.files
            if file.name.lower().startswith("readme") and file.file_type in {FileType.DOCS, FileType.DOCS_STATIC, FileType.UNKNOWN}
        ]
        readmes.sort(key=lambda file: (0 if "cn" in file.name.lower() else 1, len(file.path)))
        return [self._file_evidence(file, SourceType.DOCS, "README 提供项目介绍、启动方式或学习入口") for file in readmes]

    def _doc_files(self, graph: RepositoryIntelligenceGraph) -> list[FileNode]:
        docs = list(graph.docs) or [file for file in graph.files if file.file_type.value.startswith("docs")]
        docs.sort(key=lambda file: (0 if file.name.lower().startswith("readme") else 1, file.path))
        return docs

    def _test_evidence(self, graph: RepositoryIntelligenceGraph) -> list[EvidenceItem]:
        values: list[EvidenceItem] = []
        for command in graph.test_commands[:4]:
            values.append(
                self._make(
                    SourceType.COMMAND,
                    command,
                    command,
                    "测试命令来自 RepositoryGraph commands",
                    confidence=0.72,
                )
            )
        test_files = [file for file in graph.files if file.file_type == FileType.TEST]
        for file in test_files[:4]:
            values.append(self._file_evidence(file, SourceType.TEST, "测试文件可支持学习路径或 internal task"))
        for edge in graph.tests[:4]:
            values.append(self._edge_evidence(edge, SourceType.TEST, "测试关系来自 Test Worker"))
        return self._dedupe(values)

    def _command_evidence(self, graph: RepositoryIntelligenceGraph) -> list[EvidenceItem]:
        values = self._quality_command_evidence(graph.quality_commands)
        if values:
            return values
        for command in graph.setup_commands + graph.run_commands + graph.test_commands + graph.build_commands:
            values.append(
                self._make(
                    SourceType.COMMAND,
                    "RepositoryGraph commands",
                    command,
                    "命令来自 RepositoryGraph commands",
                    confidence=0.65,
                )
            )
        return self._dedupe(values)

    def _quality_command_evidence(self, commands: list[QualityCommand]) -> list[EvidenceItem]:
        values: list[EvidenceItem] = []
        for command in commands:
            refs = command.evidence_sources or [command.source_file or "RepositoryGraph"]
            values.append(
                self._make(
                    SourceType.COMMAND,
                    command.source_file or "RepositoryGraph command",
                    f"{command.command_type.value}: {command.command}",
                    "可验证命令来自已解析命令和证据来源：" + "、".join(refs),
                    file_path=command.source_file if command.source_file and command.source_file != "RepositoryGraph" else "",
                    line_start=command.line_start,
                    line_end=command.line_end,
                    confidence=self._confidence_value(command.confidence),
                )
            )
        return self._dedupe(values)

    def _worker_evidence(self, outputs: list[WorkerOutput], worker_name: str) -> list[EvidenceItem]:
        values: list[EvidenceItem] = []
        for output in outputs:
            if output.worker_name == worker_name:
                values.extend(output.evidence)
        return self._dedupe(values)

    def _file_evidence(self, file: FileNode, source_type: SourceType, reason: str) -> EvidenceItem:
        quote = file.content_preview or f"{file.path} ({file.language}, {file.file_type.value})"
        return self._make(
            source_type,
            file.path,
            quote,
            reason,
            file_path=file.path,
            line_start=1,
            line_end=min(file.line_count or 1, 80),
            confidence=0.82 if file.content_preview else 0.62,
        )

    def _edge_evidence(self, edge: GraphEdge, source_type: SourceType, reason: str) -> EvidenceItem:
        return self._make(
            source_type,
            f"{edge.source} -> {edge.target}",
            edge.evidence or f"{edge.source} {edge.edge_type.value} {edge.target}",
            reason,
            file_path=edge.source,
            confidence=edge.confidence,
        )

    def _make(
        self,
        source_type: SourceType,
        source_ref: str,
        quote: str,
        supports_claim: str,
        file_path: str = "",
        line_start: int | None = None,
        line_end: int | None = None,
        confidence: float = 0.7,
    ) -> EvidenceItem:
        return self.evidence.make(
            source_type,
            source_ref=source_ref,
            quote=quote,
            supports_claim=supports_claim,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            confidence=max(0.0, min(1.0, confidence)),
        )

    def _file_by_path(self, graph: RepositoryIntelligenceGraph, path: str) -> FileNode | None:
        normalized = path.replace("\\", "/")
        return next((file for file in graph.files if file.path.replace("\\", "/") == normalized), None)

    def _is_source_file(self, file: FileNode) -> bool:
        return file.file_type in {FileType.SOURCE, FileType.SOURCE_FRONTEND, FileType.SOURCE_FRONTEND_STYLE}

    def _graph_summary_quote(self, graph: RepositoryIntelligenceGraph) -> str:
        return (
            f"files={len(graph.files)}, docs={len(graph.docs)}, symbols={len(graph.symbols)}, "
            f"imports={len(graph.imports)}, tests={len(graph.tests)}, "
            f"core_directories={', '.join(graph.core_directories[:6]) or 'none'}, "
            f"entrypoints={', '.join(item.path for item in graph.entrypoints[:6]) or 'none'}"
        )

    def _confidence_value(self, value: ConfidenceLevel | str) -> float:
        raw = value.value if isinstance(value, ConfidenceLevel) else str(value)
        return {"high": 0.9, "medium": 0.7, "low": 0.45}.get(raw, 0.6)

    def _dedupe(self, values: list[EvidenceItem]) -> list[EvidenceItem]:
        result: list[EvidenceItem] = []
        seen: set[str] = set()
        for item in values:
            key = item.evidence_id
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    def _dedupe_strings(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = " ".join(str(value).strip().split())
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(normalized)
        return result

    def _is_entrypoint_question(self, question: str) -> bool:
        return any(token in question.lower() for token in ["入口", "entrypoint", "entry point", "main file"])

    def _is_core_modules_question(self, question: str) -> bool:
        return any(token in question.lower() for token in ["核心模块", "核心目录", "核心文件", "主要模块", "core module"])

    def _is_docs_question(self, question: str) -> bool:
        return any(token in question.lower() for token in ["文档", "docs", "readme", "先看"])

    def _is_beginner_task_question(self, question: str) -> bool:
        return any(token in question.lower() for token in ["新手", "入门任务", "适合", "good first", "beginner"])

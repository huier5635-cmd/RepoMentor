from __future__ import annotations

import json

from app.answer.candidate_answer_generator import CandidateAnswerGenerator
from app.answer.evaluator import Evaluator
from app.answer.optimizer import Optimizer
from app.core.intent_router import IntentRouter
from app.core.schemas import (
    AnalyzeRepoResponse,
    AnswerBundle,
    CodeExplanationWorkerInput,
    ConfidenceLevel,
    DependencyWorkerInput,
    DevelopmentWorkflowResponse,
    DevelopmentWorkflowWorkerInput,
    DocsWorkerInput,
    EvidenceItem,
    FinalAnswer,
    IssueRecommendation,
    IssueRecommendationResponse,
    IssueWorkerInput,
    LearningPathResponse,
    LearningStep,
    ModelInfo,
    RepoGraphWorkerInput,
    RepositoryRecord,
    RetrievalFilters,
    SelfCheckReport,
    SourceType,
    SuggestedAction,
    SymbolWorkerInput,
    TaskType,
    TestWorkerInput,
    RepositoryIntelligenceGraph,
)
from app.core.task_planner import TaskPlanner
from app.data_layer.hybrid_retrieval_index import HybridRetrievalIndex
from app.data_layer.repository_intelligence_graph import RepositoryIntelligenceGraphStore
from app.data_layer.shared_working_memory import SharedWorkingMemoryStore
from app.services.evidence_service import EvidenceService
from app.services.git_service import GitService
from app.services.llm_service import LLMService
from app.storage.repository_store import RepositoryStore
from app.workers.code_explanation_worker import CodeExplanationWorker
from app.workers.dependency_worker import DependencyWorker
from app.workers.development_workflow_worker import DevelopmentWorkflowWorker
from app.workers.docs_worker import DocsWorker
from app.workers.issue_worker import IssueWorker
from app.workers.repo_graph_worker import RepoGraphWorker
from app.workers.symbol_worker import SymbolWorker
from app.workers.test_worker import TestWorker


class Orchestrator:
    def __init__(self) -> None:
        self.git_service = GitService()
        self.repo_store = RepositoryStore()
        self.memory_store = SharedWorkingMemoryStore()
        self.intent_router = IntentRouter()
        self.task_planner = TaskPlanner()
        self.candidate_generator = CandidateAnswerGenerator()
        self.evaluator = Evaluator()
        self.optimizer = Optimizer()
        self.evidence_service = EvidenceService()
        self.llm_service = LLMService()
        self.indexes: dict[str, HybridRetrievalIndex] = {}

    def analyze_repo(self, repo_url: str) -> AnalyzeRepoResponse:
        prepared = self.git_service.prepare_repository(repo_url)
        memory = self.memory_store.start_session(prepared.repo_id, "analyze_repo")
        graph_store = RepositoryIntelligenceGraphStore()
        chunks = []
        evidence = []
        worker_outputs = []

        repo_graph_result = RepoGraphWorker().run(
            RepoGraphWorkerInput(
                repo_id=prepared.repo_id,
                repo_url=prepared.repo_url,
                local_path=prepared.local_path,
                owner=prepared.owner,
                name=prepared.name,
                default_branch=prepared.default_branch,
            )
        )
        graph_store.merge(repo_graph_result.graph)
        chunks.extend(repo_graph_result.chunks)
        self._record_worker(memory.session_id, repo_graph_result.worker_output, worker_outputs)

        symbol_result = SymbolWorker().run(SymbolWorkerInput(local_path=prepared.local_path, files=graph_store.graph.files))
        graph_store.add_symbols(symbol_result.symbols)
        graph_store.add_edges(symbol_result.edges)
        chunks.extend(symbol_result.chunks)
        self._record_worker(memory.session_id, symbol_result.worker_output, worker_outputs)

        dependency_result = DependencyWorker().run(DependencyWorkerInput(local_path=prepared.local_path, files=graph_store.graph.files))
        graph_store.add_edges(dependency_result.imports)
        self._record_worker(memory.session_id, dependency_result.worker_output, worker_outputs)

        docs_result = DocsWorker().run(DocsWorkerInput(local_path=prepared.local_path, files=graph_store.graph.files, graph=graph_store.graph))
        graph_store.add_files(docs_result.docs)
        graph_store.add_edges(docs_result.edges)
        chunks.extend(docs_result.chunks)
        evidence.extend(docs_result.worker_output.evidence)
        self._record_worker(memory.session_id, docs_result.worker_output, worker_outputs)

        issue_result = IssueWorker().run(IssueWorkerInput(repo_url=prepared.repo_url, owner=prepared.owner, name=prepared.name))
        repo_graph_result.repo_snapshot.issues = issue_result.issues
        chunks.extend(issue_result.chunks)
        evidence.extend(issue_result.worker_output.evidence)
        self._record_worker(memory.session_id, issue_result.worker_output, worker_outputs)

        test_result = TestWorker().run(TestWorkerInput(files=graph_store.graph.files, graph=graph_store.graph))
        graph_store.add_edges(test_result.tests)
        graph_store.graph.test_commands = sorted(set(graph_store.graph.test_commands + test_result.test_commands))
        self._record_worker(memory.session_id, test_result.worker_output, worker_outputs)

        code_result = CodeExplanationWorker().run(
            CodeExplanationWorkerInput(question=prepared.name or "repository overview", graph=graph_store.graph, chunks=chunks)
        )
        self._record_worker(memory.session_id, code_result.output, worker_outputs)

        workflow_result = DevelopmentWorkflowWorker().run(
            DevelopmentWorkflowWorkerInput(
                repo_snapshot=repo_graph_result.repo_snapshot,
                graph=graph_store.graph,
                chunks=chunks,
            )
        )
        graph_store.set_development_workflow(workflow_result.guide)
        chunks.extend(workflow_result.chunks)
        evidence.extend(workflow_result.guide.evidence)
        self._record_worker(memory.session_id, workflow_result.worker_output, worker_outputs)
        self.memory_store.add_development_workflow(memory.session_id, workflow_result.guide)

        record = RepositoryRecord(
            repo_id=prepared.repo_id,
            snapshot=repo_graph_result.repo_snapshot,
            graph=graph_store.graph,
            chunks=chunks,
            evidence=evidence,
            worker_outputs=worker_outputs,
        )
        self.repo_store.save(record)

        index = HybridRetrievalIndex()
        index.build(chunks)
        self.indexes[prepared.repo_id] = index
        summary = graph_store.summary()
        summary.update(index.summary())
        summary["shared_memory"] = {
            "session_id": memory.session_id,
            "worker_outputs": len(worker_outputs),
            "retrieved_evidence": len(self.memory_store.get_memory(memory.session_id).retrieved_evidence),
        }
        primary_language = next(iter(graph_store.graph.languages), "")
        return AnalyzeRepoResponse(
            repo_id=prepared.repo_id,
            repo_url=prepared.repo_url,
            owner=prepared.owner,
            name=prepared.name,
            default_branch=prepared.default_branch,
            local_path=prepared.local_path,
            status="done",
            files=graph_store.graph.files,
            file_tree=graph_store.graph.files,
            graph_summary=summary,
            languages=graph_store.graph.languages,
            primary_language=primary_language,
            core_directories=graph_store.graph.core_directories,
            key_files=repo_graph_result.repo_snapshot.key_files,
            readme_exists=any(item.name.lower().startswith("readme") for item in graph_store.graph.files),
            worker_outputs=worker_outputs,
            setup_commands=graph_store.graph.setup_commands,
            run_commands=graph_store.graph.run_commands,
            test_commands=graph_store.graph.test_commands,
            build_commands=graph_store.graph.build_commands,
            lint_commands=graph_store.graph.lint_commands,
            format_commands=graph_store.graph.format_commands,
            type_check_commands=graph_store.graph.type_check_commands,
            entrypoints=graph_store.graph.entrypoints,
            issues_count=len(issue_result.issues),
            session_id=memory.session_id,
        )

    def answer_question(self, repo_id: str, question: str) -> FinalAnswer:
        record = self.repo_store.load(repo_id)
        index = self._index_for(record)
        task_type = self.intent_router.classify(question)
        memory = self.memory_store.start_session(repo_id, question)
        memory.current_task = task_type.value
        memory.final_decision_trace.append(f"intent router classified task as {task_type.value}")
        self.task_planner.plan(task_type)

        retrieval_results = index.hybrid_search(self._query_for(task_type, question), filters=self._filters_for(task_type), top_k=10)
        for result in retrieval_results:
            self.memory_store.add_evidence(memory.session_id, result.evidence)

        if task_type == TaskType.CODE_EXPLANATION:
            code_result = CodeExplanationWorker().run(
                CodeExplanationWorkerInput(question=question, graph=record.graph, chunks=record.chunks)
            )
            self.memory_store.add_worker_output(memory.session_id, code_result.output)
        elif task_type == TaskType.TEST_MAPPING:
            test_output = TestWorker().run(TestWorkerInput(files=record.graph.files, graph=record.graph)).worker_output
            self.memory_store.add_worker_output(memory.session_id, test_output)
        elif task_type == TaskType.ISSUE_RECOMMENDATION:
            self._reuse_worker_output(memory.session_id, record, "Issue Worker")
        elif task_type == TaskType.DEVELOPMENT_WORKFLOW:
            self._reuse_worker_output(memory.session_id, record, "Docs Worker")
            self._reuse_worker_output(memory.session_id, record, "Issue Worker")
            self._reuse_worker_output(memory.session_id, record, "Test Worker")
            self._reuse_worker_output(memory.session_id, record, "Development Workflow Worker")
            if record.graph.development_workflow:
                self.memory_store.add_development_workflow(memory.session_id, record.graph.development_workflow)

        current_memory = self.memory_store.get_memory(memory.session_id)
        deterministic_bundle = self.candidate_generator.generate(task_type, current_memory, record.graph)
        bundle = self._maybe_generate_llm_answer(task_type, question, current_memory, record.graph, deterministic_bundle)
        if bundle.model_info.prompt_type != "not_called":
            self.memory_store.add_model_call(memory.session_id, bundle.model_info)
        self_check = self.evaluator.evaluate(bundle, record.graph)
        current_memory.final_decision_trace.append(f"evaluator suggested {self_check.suggested_action.value}")
        final = self.optimizer.optimize(bundle, self_check, current_memory.final_decision_trace)
        current_memory.final_decision_trace.append("optimizer produced final answer")
        self.memory_store.add_final_answer(memory.session_id, final)
        return final

    def _maybe_generate_llm_answer(
        self,
        task_type: TaskType,
        question: str,
        memory,
        graph: RepositoryIntelligenceGraph,
        deterministic_bundle: AnswerBundle,
    ) -> AnswerBundle:
        evidence = deterministic_bundle.evidence
        if not evidence:
            deterministic_bundle.model_info = ModelInfo(
                provider=self.llm_service.provider_name,
                model="not-called",
                prompt_type="not_called",
                evidence_count=0,
                success=False,
                used_llm=False,
                fallback_to_mock=False,
                error_message="evidence empty; LLM was not called",
            )
            memory.final_decision_trace.append("llm skipped because evidence_count=0")
            return deterministic_bundle

        system_prompt = self._repoqa_system_prompt(task_type)
        user_prompt = self._repoqa_user_prompt(task_type, question, graph, deterministic_bundle, memory.unresolved_uncertainties)
        result = self.llm_service.generate(
            user_prompt,
            system=system_prompt,
            prompt_type=task_type.value,
            evidence_count=len(evidence),
        )
        deterministic_bundle.model_info = result.model_info
        deterministic_bundle.raw_model_output = result.text

        if not result.model_info.used_llm:
            memory.final_decision_trace.append("llm returned mock/fallback; deterministic answer retained")
            return deterministic_bundle

        parsed = self._parse_llm_answer(result.text)
        if not parsed:
            deterministic_bundle.risks.append("模型输出无法解析为结构化答案，已保留确定性答案。")
            memory.final_decision_trace.append("llm output was not parseable; deterministic answer retained")
            return deterministic_bundle

        allowed_commands = self._known_commands(graph, deterministic_bundle)
        commands, rejected_commands = self._filter_llm_commands(parsed.get("verifiable_commands", []), allowed_commands)
        risks = self._as_string_list(parsed.get("risks")) or deterministic_bundle.risks
        if rejected_commands:
            risks.append("模型输出包含无证据命令，已从可验证命令中移除：" + "；".join(rejected_commands))

        return AnswerBundle(
            conclusion=str(parsed.get("conclusion") or deterministic_bundle.conclusion).strip(),
            task_type=deterministic_bundle.task_type,
            answer_type=deterministic_bundle.answer_type,
            evidence=evidence,
            steps=self._as_string_list(parsed.get("steps")) or deterministic_bundle.steps,
            risks=risks,
            verifiable_commands=commands or deterministic_bundle.verifiable_commands,
            confidence=deterministic_bundle.confidence,
            uncertainties=self._as_string_list(parsed.get("uncertainties")) or deterministic_bundle.uncertainties,
            model_info=result.model_info,
            raw_model_output=result.text,
        )

    def _repoqa_system_prompt(self, task_type: TaskType) -> str:
        base = [
            "你是 RepoMentor 的仓库学习助手。",
            "你只能基于提供的 evidence 回答。",
            "如果 evidence 不足，必须明确说“当前仓库证据不足”。",
            "不要编造文件名、函数名、命令、Issue 编号、PR 编号或测试关系。",
            "不要声称你运行过命令，除非 evidence 明确说明。",
            "回答必须包含：结论、依据、操作步骤、风险提示、可验证命令。",
            "如果用户问怎么启动、怎么测试或怎么安装，必须优先使用 evidence 中的命令，不要自己猜常见命令。",
            "请只输出 JSON，不要输出 Markdown。",
            'JSON 字段必须是：{"conclusion": str, "basis": [str], "steps": [str], "risks": [str], "verifiable_commands": [str], "uncertainties": [str]}',
        ]
        if task_type == TaskType.SETUP_RUN:
            base.append(
                "setup_run 回答的 steps 必须按 1. 推荐启动方式 2. 可选 demo 命令 3. 评估命令 4. 测试命令 5. 风险提示 6. 证据来源 分组。"
            )
        return "\n".join(base)

    def _repoqa_user_prompt(
        self,
        task_type: TaskType,
        question: str,
        graph: RepositoryIntelligenceGraph,
        bundle: AnswerBundle,
        uncertainties: list[str],
    ) -> str:
        payload = {
            "用户问题": question,
            "任务类型": task_type.value,
            "仓库结构摘要": self._graph_summary_for_prompt(graph),
            "检索到的证据": [self._evidence_for_prompt(item) for item in bundle.evidence[:10]],
            "可验证命令": bundle.verifiable_commands,
            "确定性候选答案": {
                "conclusion": bundle.conclusion,
                "steps": bundle.steps,
                "risks": bundle.risks,
                "verifiable_commands": bundle.verifiable_commands,
            },
            "不确定点": uncertainties + bundle.uncertainties,
            "要求": "请基于以上证据回答，不要使用 evidence 之外的事实。",
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _graph_summary_for_prompt(self, graph: RepositoryIntelligenceGraph) -> dict[str, object]:
        summary = self._graph_summary(graph)
        return {
            "files": summary.get("files"),
            "symbols": summary.get("symbols"),
            "imports": summary.get("imports"),
            "tests": summary.get("tests"),
            "docs": summary.get("docs"),
            "quality_commands": summary.get("quality_commands"),
            "development_workflow": summary.get("development_workflow"),
            "entrypoints": [item.path for item in graph.entrypoints[:8]],
            "core_directories": graph.core_directories[:8],
        }

    def _evidence_for_prompt(self, item: EvidenceItem) -> dict[str, object]:
        quote = item.quote.replace("\n", " ").strip()
        if len(quote) > 700:
            quote = quote[:700] + "..."
        return {
            "evidence_id": item.evidence_id,
            "source_type": item.source_type.value,
            "source_ref": item.source_ref,
            "file_path": item.file_path,
            "issue_number": item.issue_number,
            "line_start": item.line_start,
            "line_end": item.line_end,
            "quote": quote,
            "supports_claim": item.supports_claim,
            "confidence": item.confidence,
        }

    def _parse_llm_answer(self, text: str) -> dict[str, object]:
        cleaned = (text or "").strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _known_commands(self, graph: RepositoryIntelligenceGraph, bundle: AnswerBundle) -> set[str]:
        commands = set(bundle.verifiable_commands)
        commands.update(graph.setup_commands + graph.run_commands + graph.test_commands + graph.build_commands)
        commands.update(graph.lint_commands + graph.format_commands + graph.type_check_commands)
        commands.update(command.command for command in graph.quality_commands)
        for rule in graph.ci_rules:
            commands.update(command.command for command in rule.commands)
        return {self._normalize_command(command) for command in commands if command}

    def _filter_llm_commands(self, values: object, allowed_commands: set[str]) -> tuple[list[str], list[str]]:
        accepted: list[str] = []
        rejected: list[str] = []
        for item in self._as_string_list(values):
            normalized = self._normalize_command(item)
            if normalized in allowed_commands:
                accepted.append(normalized)
            else:
                rejected.append(item)
        return self._dedupe_list(accepted), self._dedupe_list(rejected)

    def _as_string_list(self, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()] if str(value).strip() else []

    def _dedupe_list(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    def generate_learning_path(self, repo_id: str) -> LearningPathResponse:
        record = self.repo_store.load(repo_id)
        graph = record.graph
        workflow = graph.development_workflow
        learning_evidence = self.candidate_generator.evidence_builder.build_learning_path_evidence(graph, record.worker_outputs)
        docs_evidence = [item for item in learning_evidence if item.source_type.value == "docs"]
        command_evidence = [item for item in learning_evidence if item.source_type.value == "command"]
        code_evidence = [item for item in learning_evidence if item.source_type.value in {"code", "graph", "test", "tests", "config", "build"}]
        entrypoint_evidence = [
            item for item in learning_evidence
            if any(entrypoint.path in (item.file_path or item.source_ref or item.quote) for entrypoint in graph.entrypoints)
        ]
        test_evidence = [item for item in learning_evidence if item.source_type.value in {"test", "tests", "command"}]
        workflow_evidence = [item for item in learning_evidence if item.source_type.value in {"workflow", "contributing", "ci", "style", "pr_template", "command"}]
        task_evidence = [item for item in learning_evidence if item.source_type.value in {"issue", "issues", "internal_suggestion", "graph", "docs", "test"}]
        issue_evidence = [output.evidence[0] for output in record.worker_outputs if output.worker_name == "Issue Worker" and output.evidence]
        steps: list[LearningStep] = []

        def add(title: str, reason: str, evidence=None) -> None:
            steps.append(
                LearningStep(
                    order=len(steps) + 1,
                    title=title,
                    reason=reason,
                    evidence=list(evidence or [])[:3],
                )
            )

        readme = next((item for item in graph.files if item.name.lower() == "readme.md"), None)
        add(
            "阅读 README",
            f"先读 {readme.path}，建立项目目标、安装方式和使用入口。" if readme else "未找到 README.md；先从文件树和配置文件建立项目上下文。",
            docs_evidence,
        )
        add(
            "跑通安装和启动",
            "根据已检测命令验证本地环境：" + "；".join(graph.run_commands[:4])
            if graph.run_commands
            else "未检测到启动命令；请优先查看 README、pyproject.toml、package.json 或 Makefile。",
            command_evidence or docs_evidence,
        )
        add(
            "阅读核心目录",
            "优先阅读核心目录：" + "；".join(graph.core_directories[:6])
            if graph.core_directories
            else "未检测到核心目录；当前仓库文件结构不足以给出目录优先级。",
            code_evidence,
        )
        add(
            "阅读入口文件",
            "从入口文件开始追踪主流程：" + "；".join(item.path for item in graph.entrypoints[:6])
            if graph.entrypoints
            else "未检测到入口文件候选；可先按核心目录和 README 的模块说明阅读。",
            entrypoint_evidence or code_evidence,
        )
        add(
            "阅读测试",
            "从测试文件和测试命令反推行为边界：" + "；".join(graph.test_commands[:4])
            if graph.test_commands
            else "未检测到测试命令；请查看 tests 目录或 CI 工作流是否提供验证方式。",
            test_evidence,
        )
        add(
            "学习开发流程",
            "阅读开发流程、贡献规则、质量命令和 CI 检查；已提取 checklist 数量：" + str(len(workflow.new_contributor_checklist))
            if workflow
            else "未生成 Development Workflow；请查看 Debug Console 的工作器输出。",
            workflow_evidence,
        )
        add(
            "选择推荐议题",
            f"已获取 {len(record.snapshot.issues)} 个 open issue，可按难度、标签和更新时间选择小范围任务。"
            if record.snapshot.issues
            else "未找到可推荐 open issues；改用基于 README、测试、入口文件和文档的 internal first tasks。",
            issue_evidence or task_evidence,
        )

        risks = []
        if not readme:
            risks.append("未找到 README.md。")
        if not graph.run_commands:
            risks.append("未检测到启动命令。")
        if not graph.test_commands:
            risks.append("未检测到测试命令。")
        if workflow:
            risks.extend(workflow.uncertainties)
        evidence_coverage = sum(1 for step in steps if step.evidence) / max(1, len(steps))
        return LearningPathResponse(
            conclusion="学习路径由确定性仓库结构、配置文件、开发流程和 GitHub issue 数据生成，不依赖真实 LLM。",
            steps=steps,
            risks=risks,
            verifiable_commands=graph.run_commands + graph.test_commands + graph.build_commands + graph.lint_commands + graph.format_commands,
            self_check=SelfCheckReport(
                passed=bool(graph.files),
                evidence_coverage=round(evidence_coverage, 4),
                missing_evidence=[] if evidence_coverage >= 0.5 else ["learning path evidence coverage is low"],
                suggested_action=SuggestedAction.ACCEPT if graph.files else SuggestedAction.RETRIEVE_MORE,
            ),
        )

    def get_development_workflow(self, repo_id: str) -> DevelopmentWorkflowResponse:
        record = self.repo_store.load(repo_id)
        guide = record.graph.development_workflow
        if guide is None:
            bundle = self.candidate_generator.generate(
                TaskType.DEVELOPMENT_WORKFLOW,
                self.memory_store.start_session(repo_id, "development workflow"),
                record.graph,
            )
            self_check = self.evaluator.evaluate(bundle, record.graph)
            final = self.optimizer.optimize(bundle, self_check, ["development workflow guide missing"])
            return DevelopmentWorkflowResponse(
                conclusion=final.conclusion,
                quality_commands=record.graph.quality_commands,
                risks=final.risks,
                verifiable_commands=final.verifiable_commands,
                self_check=final.self_check,
                uncertainties=["Development Workflow Worker output missing"],
            )

        bundle = self.candidate_generator._development_workflow_answer(guide.evidence, record.graph)
        self_check = self.evaluator.evaluate(bundle, record.graph)
        final = self.optimizer.optimize(bundle, self_check, ["development workflow endpoint formatted guide"])
        return DevelopmentWorkflowResponse(
            conclusion=final.conclusion,
            quality_commands=record.graph.quality_commands,
            setup_steps=guide.setup_steps,
            development_commands=guide.development_commands,
            test_commands=guide.test_commands,
            lint_commands=guide.lint_commands,
            format_commands=guide.format_commands,
            type_check_commands=guide.type_check_commands,
            build_commands=guide.build_commands,
            branch_rules=guide.branch_rules,
            commit_rules=guide.commit_rules,
            contribution_rules=guide.contribution_rules,
            pull_request_rules=guide.pull_request_rules,
            ci_rules=guide.ci_rules,
            code_style_rules=guide.code_style_rules,
            setup_rules=guide.setup_rules,
            test_rules=guide.test_rules,
            documentation_references=guide.documentation_references,
            project_safety_policies=guide.project_safety_policies,
            new_contributor_checklist=guide.new_contributor_checklist,
            evidence_docs=final.evidence_docs,
            evidence_code=final.evidence_code,
            evidence_issues=final.evidence_issues,
            risks=final.risks,
            verifiable_commands=final.verifiable_commands,
            self_check=final.self_check,
            uncertainties=guide.uncertainties,
        )

    def recommend_issues(self, repo_id: str) -> IssueRecommendationResponse:
        record = self.repo_store.load(repo_id)
        recommendations: list[IssueRecommendation] = []
        if not record.snapshot.issues:
            recommendations = self._internal_issue_fallbacks(record)
            self_check = SelfCheckReport(
                passed=bool(recommendations),
                evidence_coverage=0.65 if recommendations else 0.0,
                missing_evidence=["当前仓库没有 GitHub open issue 数据"],
                suggested_action=SuggestedAction.ACCEPT if recommendations else SuggestedAction.RETRIEVE_MORE,
            )
            return IssueRecommendationResponse(
                issues=recommendations,
                self_check=self_check,
                message="当前仓库没有 open issue，因此这是基于仓库结构生成的入门练习任务。",
            )
        for issue in sorted(record.snapshot.issues, key=lambda item: item.recommendation_score, reverse=True)[:10]:
            evidence = [
                self.evidence_service.make(
                    SourceType.ISSUES,
                    f"issue #{issue.issue_number}",
                    issue.title,
                    "recommendation references a real GitHub issue",
                    issue_number=issue.issue_number,
                    confidence=0.95,
                )
            ]
            reason_parts = [
                f"labels={', '.join(issue.labels) or 'none'}",
                f"comments={issue.comments_count}",
                f"type={issue.issue_type}",
                f"skills={', '.join(issue.skill_tags) or 'unknown'}",
            ]
            recommendations.append(
                IssueRecommendation(
                    issue_number=issue.issue_number,
                    title=issue.title,
                    difficulty=issue.difficulty,
                    skill_tags=issue.skill_tags,
                    recommendation_reason="; ".join(reason_parts),
                    suggested_first_steps=[
                        "阅读 issue 描述和最近评论",
                        "在本地运行相关测试或文档构建命令",
                        "先提交一个小范围变更并补充验证说明",
                    ],
                    evidence=evidence,
                    score=issue.recommendation_score,
                )
            )
        self_check = SelfCheckReport(
            passed=bool(recommendations),
            evidence_coverage=1.0 if recommendations else 0.0,
            missing_evidence=[] if recommendations else ["no GitHub issues available"],
            suggested_action=SuggestedAction.ACCEPT if recommendations else SuggestedAction.RETRIEVE_MORE,
        )
        return IssueRecommendationResponse(
            issues=recommendations,
            self_check=self_check,
            message="" if recommendations else "未找到可推荐 open issues",
        )

    def _internal_issue_fallbacks(self, record: RepositoryRecord) -> list[IssueRecommendation]:
        graph = record.graph
        files = {item.path for item in graph.files}
        docs = {item.path for item in graph.docs}
        test_files = [item.path for item in graph.files if item.file_type.value == "test"]
        tasks: list[tuple[str, list[str], str, ConfidenceLevel, float, str]] = []

        if graph.test_commands:
            test_command = self._preferred_command(graph.test_commands, ["python -m pytest tests", "pytest"])
            tasks.append(
                (
                    f"跑通 {test_command}",
                    [f"运行：{test_command}", "记录环境、依赖安装方式和失败信息", "把结果反馈到学习笔记或 README 检查清单"],
                    "检测到测试命令，适合作为低风险验证任务。",
                    ConfidenceLevel.MEDIUM,
                    0.62,
                    test_command,
                )
            )
        if "docs/architecture.md" in files:
            tasks.append(
                (
                    "阅读 docs/architecture.md 并对照 src/agent/resilience_agent.py",
                    ["阅读 docs/architecture.md", "打开 src/agent/resilience_agent.py", "写下文档中的架构模块如何落到源码类和函数"],
                    "仓库同时包含架构文档和核心 agent 源码，适合做代码阅读入门任务。",
                    ConfidenceLevel.MEDIUM,
                    0.6,
                    "docs/architecture.md",
                )
            )
        if "scripts/run_demo.py" in files:
            tasks.append(
                (
                    "运行 python scripts/run_demo.py",
                    ["先运行：pip install -r requirements.txt", "再运行：python scripts/run_demo.py", "记录 demo 输出和失败条件"],
                    "仓库包含 demo 脚本，适合作为 setup 入门任务。",
                    ConfidenceLevel.MEDIUM,
                    0.59,
                    "scripts/run_demo.py",
                )
            )
        if any(item.name.lower().startswith("readme") for item in graph.files):
            tasks.append(
                (
                    "检查 README quick start 命令是否能复现",
                    ["阅读 README 中的 quick start 或安装/运行段落", "逐条运行已检测到的启动命令", "记录命令是否仍然可复现"],
                    "README 存在，启动命令核验是新贡献者友好的入门练习。",
                    ConfidenceLevel.MEDIUM,
                    0.58,
                    "README",
                )
            )
        if "docs/reproducibility_checklist.md" in files:
            tasks.append(
                (
                    "检查 docs/reproducibility_checklist.md",
                    ["阅读可复现性清单", "对照当前测试/评估命令逐项核对", "补充缺失的本地执行记录"],
                    "仓库包含可复现性清单，适合做文档核验任务。",
                    ConfidenceLevel.MEDIUM,
                    0.54,
                    "docs/reproducibility_checklist.md",
                )
            )
        if test_files:
            safety_test = "tests/test_safety_contract.py" if "tests/test_safety_contract.py" in test_files else test_files[0]
            tasks.append(
                (
                    f"阅读 {safety_test} 理解安全约束",
                    [f"打开 {safety_test}", "查找它覆盖的源码模块", "补充运行该测试的命令或注意事项"],
                    "仓库已有测试文件，适合从测试说明开始做小范围贡献。",
                    ConfidenceLevel.LOW,
                    0.48,
                    safety_test,
                )
            )
        if "scripts/run_stress_test.py" in files:
            tasks.append(
                (
                    "运行 stress test 并查看报告",
                    ["运行：python scripts/run_stress_test.py", "检查输出报告或日志", "记录资源、耗时和失败条件"],
                    "仓库包含 stress test 脚本，可作为结构化练习任务。",
                    ConfidenceLevel.MEDIUM,
                    0.56,
                    "scripts/run_stress_test.py",
                )
            )

        if not tasks:
            tasks.append(
                (
                    "阅读仓库结构并写一份新手导览",
                    ["查看核心目录", "标记源码、测试、文档和配置文件", "整理一个从 README 到测试命令的最小路径"],
                    "没有 open issue 时，结构导览是低风险入门任务。",
                    ConfidenceLevel.LOW,
                    0.42,
                    "RepositoryIntelligenceGraph",
                )
            )

        recommendations: list[IssueRecommendation] = []
        for index, (title, steps, reason, confidence, score, source_ref) in enumerate(tasks[:6], start=1):
            evidence = [
                self.evidence_service.make(
                    SourceType.INTERNAL_SUGGESTION,
                    source_ref,
                    f"当前仓库没有 open issue；任务基于 {source_ref} 生成。",
                    "internal first task generated from repository structure",
                    file_path=source_ref if source_ref in files else "",
                    confidence=score,
                )
            ]
            recommendations.append(
                IssueRecommendation(
                    issue_number=-index,
                    title=title,
                    difficulty="easy" if confidence == ConfidenceLevel.MEDIUM else "medium",
                    skill_tags=self._fallback_task_tags(title),
                    recommendation_reason=reason + " 这不是 GitHub Issue，而是内部建议任务。",
                    suggested_first_steps=steps,
                    evidence=evidence,
                    score=score,
                    source=SourceType.INTERNAL_SUGGESTION.value,
                    confidence=confidence,
                    is_github_issue=False,
                )
            )
        return recommendations

    def _preferred_command(self, commands: list[str], preferred: list[str]) -> str:
        normalized = {self._normalize_command(command): self._normalize_command(command) for command in commands}
        for item in preferred:
            command = normalized.get(self._normalize_command(item))
            if command:
                return command
        return self._normalize_command(commands[0])

    def _fallback_task_tags(self, title: str) -> list[str]:
        text = title.lower()
        tags: list[str] = []
        if any(token in text for token in ["readme", "docs", "文档", "architecture"]):
            tags.append("docs")
        if any(token in text for token in ["test", "pytest", "测试"]):
            tags.append("test")
        if any(token in text for token in ["启动", "demo", "quick start", "安装"]):
            tags.append("setup")
        if any(token in text for token in ["源码", "阅读", "对照", "约束", "contract"]):
            tags.append("code-reading")
        return tags or ["docs", "code-reading"]

    def get_trace(self, session_id: str) -> dict[str, object]:
        return self.memory_store.export_trace(session_id)

    def get_llm_status(self) -> dict[str, object]:
        return self.llm_service.status()

    def configure_llm(self, payload: dict[str, object]) -> dict[str, object]:
        return self.llm_service.configure(
            str(payload.get("provider") or "mock"),
            deepseek_api_key=str(payload.get("deepseek_api_key") or ""),
            deepseek_model=str(payload.get("deepseek_model") or "deepseek-chat"),
            deepseek_base_url=str(payload.get("deepseek_base_url") or "https://api.deepseek.com"),
            openai_api_key=str(payload.get("openai_api_key") or ""),
            openai_model=str(payload.get("openai_model") or ""),
            openai_base_url=str(payload.get("openai_base_url") or "https://api.openai.com/v1"),
        )

    def get_model_status(self) -> dict[str, object]:
        return self.llm_service.status()

    def configure_model(self, payload: dict[str, object]) -> dict[str, object]:
        return self.llm_service.configure_model(
            provider=str(payload.get("provider") or "mock"),
            model=str(payload.get("model") or ""),
            base_url=str(payload.get("base_url") or ""),
            api_key=str(payload.get("api_key") or ""),
            persist=bool(payload.get("persist") or False),
        )

    def test_model_connection(self) -> dict[str, object]:
        return self.llm_service.test_connection()

    def get_graph(self, repo_id: str) -> dict[str, object]:
        record = self.repo_store.load(repo_id)
        index = self._index_for(record)
        graph_summary = self._graph_summary(record.graph)
        return {
            "repo_id": record.repo_id,
            "snapshot": record.snapshot,
            "raw_graph": record.graph,
            "files": record.graph.files,
            "symbols": record.graph.symbols,
            "imports": record.graph.imports,
            "tests": record.graph.tests,
            "docs": record.graph.docs,
            "build_scripts": record.graph.build_scripts,
            "development_workflow": record.graph.development_workflow,
            "quality_commands": record.graph.quality_commands,
            "contributing_rules": record.graph.contributing_rules,
            "ci_rules": record.graph.ci_rules,
            "languages": record.graph.languages,
            "primary_language": next(iter(record.graph.languages), ""),
            "core_directories": record.graph.core_directories,
            "key_files": record.snapshot.key_files or record.graph.key_files,
            "readme_exists": any(item.name.lower().startswith("readme") for item in record.graph.files),
            "entrypoints": record.graph.entrypoints,
            "commands": {
                "setup": record.graph.setup_commands,
                "run": record.graph.run_commands,
                "test": record.graph.test_commands,
                "build": record.graph.build_commands,
                "lint": record.graph.lint_commands,
                "format": record.graph.format_commands,
                "type_check": record.graph.type_check_commands,
            },
            "issues_count": len(record.snapshot.issues),
            "graph_summary": graph_summary,
            "index": index.summary(),
        }

    def _graph_summary(self, graph: RepositoryIntelligenceGraph) -> dict[str, object]:
        return RepositoryIntelligenceGraphStore(graph).summary()

    def _record_worker(self, session_id: str, output, worker_outputs: list) -> None:
        worker_outputs.append(output)
        self.memory_store.add_worker_output(session_id, output)

    def _reuse_worker_output(self, session_id: str, record: RepositoryRecord, worker_name: str) -> None:
        output = next((item for item in record.worker_outputs if item.worker_name == worker_name), None)
        if output:
            self.memory_store.add_worker_output(session_id, output)

    def _index_for(self, record: RepositoryRecord) -> HybridRetrievalIndex:
        index = self.indexes.get(record.repo_id)
        if index is None:
            index = HybridRetrievalIndex()
            index.build(record.chunks)
            self.indexes[record.repo_id] = index
        return index

    def _filters_for(self, task_type: TaskType) -> RetrievalFilters | None:
        if task_type == TaskType.SETUP_RUN:
            return RetrievalFilters(source_type=["docs", "config", "build", "workflow"])
        if task_type == TaskType.ISSUE_RECOMMENDATION:
            return RetrievalFilters(source_type=["issue"])
        if task_type == TaskType.CODE_EXPLANATION:
            return RetrievalFilters(source_type=["code", "test", "docs"])
        if task_type == TaskType.DEVELOPMENT_WORKFLOW:
            return RetrievalFilters(source_type=["workflow", "contributing", "ci", "style", "pr_template", "docs", "config", "build"])
        return None

    def _query_for(self, task_type: TaskType, question: str) -> str:
        if task_type == TaskType.SETUP_RUN:
            return f"{question} install setup start run test build README package pyproject"
        if task_type == TaskType.LEARNING_PATH:
            return f"{question} README docs examples src tests entrypoint CONTRIBUTING CI lint format"
        if task_type == TaskType.DEVELOPMENT_WORKFLOW:
            return f"{question} CONTRIBUTING README PR branch commit lint format test CI workflow pull_request"
        return question

    def _normalize_command(self, command: str) -> str:
        return " ".join(command.replace("\\", "/").strip().split())


orchestrator = Orchestrator()

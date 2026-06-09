from __future__ import annotations

import hashlib
import re
from pathlib import Path

from app.core.schemas import (
    ArchitectureTour,
    BilingualDocView,
    ChangeImpactRequest,
    ChangeImpactResponse,
    CommandType,
    ConfidenceLevel,
    EdgeType,
    EvidenceItem,
    IssueRecommendation,
    IssueRecommendationResponse,
    LearningAgentDebugBundle,
    LearningCheckRequest,
    LearningCheckResponse,
    LearningPathStepV2,
    LearningPathV2Response,
    ModuleStudyCard,
    OnboardingDebtReport,
    ProjectGlossary,
    ProjectGlossaryTerm,
    QualityCommand,
    RepositoryRecord,
    SelfCheckReport,
    SourceType,
    SuggestedAction,
    TranslationChunkRecord,
    TutorialDraft,
    TutorialStep,
)
from app.services.evidence_service import EvidenceService


class LearningAgentService:
    """Deterministic learning artifacts built only from repository graph facts."""

    def __init__(self, repo_store) -> None:
        self.repo_store = repo_store
        self.evidence_service = EvidenceService()

    def learning_path_v2(self, repo_id: str) -> LearningPathV2Response:
        record = self.repo_store.load(repo_id)
        graph = record.graph
        readme = self._preferred_readme(record)
        architecture_doc = self._find_existing_file(record, ["docs/architecture.md", "architecture.md"])
        entry_files = self._entry_files(record)[:4]
        core_files = self._core_source_files(record)[:6]
        test_files = self._test_files(record)[:6]
        workflow = graph.development_workflow
        setup_command = self._preferred_quality_command(record, CommandType.SETUP)
        run_command = self._preferred_run_command(record)
        test_command = self._preferred_quality_command(record, CommandType.TEST)
        contribution_tasks = self.contribution_funnel(repo_id).issues
        change_target = entry_files[0] if entry_files else (core_files[0] if core_files else "")

        steps = [
            self._step(
                "project-goal",
                "确认项目目标",
                "用 README 和架构文档建立项目要解决的问题、主要用户和最小运行目标。",
                "先知道项目为什么存在，后续读代码才不会只是在文件树里迷路。",
                ["README 结构", "项目名称", "核心目录"],
                self._existing_paths([readme, architecture_doc]),
                [],
                ["能用一句话说明项目目标", "能指出目标来自哪些文档而不是猜测"],
                self._worked_example("从 README 标题、简介和 docs/architecture.md 提取项目目标。", self._existing_paths([readme, architecture_doc])),
                ["这个项目主要解决什么问题？", "哪份文档支持你的判断？"],
                ["只根据仓库名猜项目用途", "忽略 README 中的限制和前提"],
                self._evidence_for_paths(record, self._existing_paths([readme, architecture_doc]), "学习路径：确认项目目标"),
                [] if readme else ["未发现 README，项目目标只能从目录和文件名低置信度推断。"],
            ),
            self._step(
                "setup-run",
                "跑通最小启动链路",
                "先安装依赖，再运行推荐 demo 或主入口，最后用测试命令验证环境。",
                "能运行的项目比能读懂的项目更容易学习；启动失败也能暴露缺失依赖或文档债务。",
                ["依赖安装", "命令行运行", "测试入口"],
                self._existing_paths([readme, *(entry_files[:2])]),
                self._command_strings([setup_command, run_command, test_command]),
                ["依赖能安装", "demo 或主入口能执行", "测试命令能找到测试文件"],
                self._worked_example("推荐顺序：安装依赖 -> 运行 demo/入口 -> 跑测试。", self._existing_paths([readme, *(entry_files[:1])]), self._command_strings([setup_command, run_command, test_command])),
                ["启动命令是什么？", "测试命令是什么？", "失败时优先检查哪份文档？"],
                ["把评估脚本当成普通启动命令", "没有记录失败输出", "跳过依赖安装直接运行脚本"],
                self._command_evidence(record, [setup_command, run_command, test_command]),
                [] if (setup_command or run_command) else ["未发现明确 setup/run 命令。"],
            ),
            self._step(
                "main-flow",
                "追踪主流程入口",
                "从入口文件向下看导入关系和关键符号，建立从命令到代码路径的映射。",
                "入口文件连接了用户命令和内部模块，是理解架构的最短路径。",
                ["entrypoint", "import graph", "function/class symbol"],
                entry_files,
                self._command_strings([run_command]),
                ["能指出命令会触达哪些入口文件", "能列出入口文件依赖的核心模块"],
                self._worked_example("打开入口文件，沿 imports 边查看下游模块。", entry_files[:3], self._command_strings([run_command])),
                ["主入口文件有哪些？", "入口依赖的第一个核心模块是什么？"],
                ["把 __init__.py 当成主流程入口", "只看文件名不看导入关系"],
                self._evidence_for_paths(record, entry_files, "学习路径：追踪主流程入口"),
                [] if entry_files else ["未发现高置信入口文件。"],
            ),
            self._step(
                "core-modules",
                "阅读核心模块",
                "按模块卡片顺序阅读核心源码、符号、上游调用者和下游依赖。",
                "模块卡能把源码阅读拆成可完成的小任务。",
                ["module role", "upstream caller", "downstream dependency"],
                core_files,
                [],
                ["能说明每个核心文件的系统角色", "能指出相关测试或文档"],
                self._worked_example("选择一个核心文件，查看 key_symbols、related_tests、related_docs。", core_files[:3]),
                ["这个模块为什么存在？", "改它可能影响哪些测试？"],
                ["一口气读完整个 src 目录", "只看函数名不看测试边界"],
                self._evidence_for_paths(record, core_files[:4], "学习路径：阅读核心模块"),
                [] if core_files else ["未发现可优先阅读的核心源码文件。"],
            ),
            self._step(
                "tests-as-boundary",
                "用测试理解行为边界",
                "从 tests 文件和 tests 边反推哪些行为已经被保护。",
                "测试通常比文档更接近真实行为约束，适合新贡献者建立安全边界。",
                ["test edge", "behavior boundary", "regression"],
                test_files,
                self._command_strings([test_command]),
                ["能说出至少一个测试覆盖的源码文件", "能运行对应测试命令"],
                self._worked_example("先读测试文件名，再查看 test edge 指向的源码。", test_files[:3], self._command_strings([test_command])),
                ["哪些测试能保护主流程？", "新增改动前应该跑哪条命令？"],
                ["只运行 demo 不运行测试", "看测试断言时忽略测试数据和 fixture"],
                self._evidence_for_paths(record, test_files[:4], "学习路径：用测试理解行为边界"),
                [] if test_files else ["未发现测试文件。"],
            ),
            self._step(
                "development-workflow",
                "学习开发流程",
                "查看安装、测试、lint、format、CI、PR 或贡献规则，确定提交前检查清单。",
                "贡献前先知道项目如何验证质量，可以减少无效 PR。",
                ["quality command", "CI", "PR checklist", "contributing"],
                self._workflow_files(record),
                self._command_strings(self._quality_commands(record)[:8]),
                ["能列出提交前必须运行的命令", "能明确缺失的流程文档"],
                self._worked_example("把质量命令按 setup/run/test/lint/build 分类，再标记缺失项。", self._workflow_files(record), self._command_strings(self._quality_commands(record)[:5])),
                ["项目是否有 CONTRIBUTING？", "是否有 CI？", "提交前跑什么命令？"],
                ["把业务安全说明误当成贡献规范", "把评估脚本和主启动脚本混在一起"],
                list(workflow.evidence[:5]) if workflow else self._command_evidence(record, self._quality_commands(record)[:5]),
                self._workflow_uncertainties(record),
            ),
            self._step(
                "first-task",
                "选择第一个低风险任务",
                "从 GitHub issue 或 internal first tasks 中选择一个 docs/test/setup/code-reading 任务。",
                "低风险任务能让新贡献者完成一次闭环，而不需要马上改核心逻辑。",
                ["good first task", "internal suggestion", "scope control"],
                self._task_related_files(contribution_tasks[:2]),
                self._task_related_commands(contribution_tasks[:2]),
                ["能说明任务不是凭空生成", "能写出预期输出和第一步"],
                self._worked_example("如果 open issue 为 0，选择结构生成的 internal first task。", self._task_related_files(contribution_tasks[:1]), self._task_related_commands(contribution_tasks[:1])),
                ["这个任务是否为 GitHub Issue？", "为什么适合新贡献者？"],
                ["把内部练习任务误认为真实 issue", "选择没有验证命令的任务"],
                [ev for task in contribution_tasks[:3] for ev in task.evidence[:2]],
                [] if contribution_tasks else ["未能生成入门任务。"],
            ),
            self._step(
                "change-rehearsal",
                "做一次改动前演练",
                "选一个文件或符号，查看影响模块、测试、文档和必须运行的命令。",
                "正式修改前先演练影响面，可以降低破坏主流程的风险。",
                ["impact analysis", "test impact", "docs impact"],
                [change_target] if change_target else [],
                self._command_strings([test_command]),
                ["能列出改动前必读文件", "能列出必须运行的测试命令"],
                self._worked_example("在改入口或核心模块前，用 Change Impact Rehearsal 查看影响面。", [change_target] if change_target else [], self._command_strings([test_command])),
                ["改这个文件会影响哪些测试？", "哪些文档需要重看？"],
                ["直接改代码不查测试边", "低置信影响面没有标记不确定性"],
                self._evidence_for_paths(record, [change_target] if change_target else [], "学习路径：改动前演练"),
                [] if change_target else ["缺少可用于演练的入口或核心源码文件。"],
            ),
        ]
        evidence_count = sum(1 for item in steps if item.evidence)
        coverage = evidence_count / max(1, len(steps))
        return LearningPathV2Response(
            repo_id=record.repo_id,
            conclusion="学习路径 V2 已按项目目标、启动、主流程、核心模块、测试边界、开发流程、入门任务和改动演练组织；所有文件和命令均来自仓库图谱。",
            steps=steps,
            evidence_coverage=round(coverage, 4),
            hallucination_guardrails=[
                "文件路径必须存在于 RepositoryIntelligenceGraph。",
                "命令必须来自 README、配置、脚本或 Development Workflow Worker 的确定性抽取。",
                "没有 CONTRIBUTING、CI、Issue 模板时明确标记缺失，不生成假规则。",
                "internal first tasks 明确标记为不是 GitHub Issue。",
            ],
            self_check=SelfCheckReport(
                passed=bool(record.graph.files) and coverage >= 0.5,
                evidence_coverage=round(coverage, 4),
                missing_evidence=[] if coverage >= 0.5 else ["LearningPathV2 evidence coverage below 0.5"],
                suggested_action=SuggestedAction.ACCEPT if coverage >= 0.5 else SuggestedAction.RETRIEVE_MORE,
            ),
        )

    def architecture_tour(self, repo_id: str, audience: str = "newcomer") -> ArchitectureTour:
        record = self.repo_store.load(repo_id)
        graph = record.graph
        readme = self._preferred_readme(record)
        architecture_doc = self._find_existing_file(record, ["docs/architecture.md", "architecture.md"])
        docs = self._doc_paths(record)
        tests = self._test_files(record)
        entrypoints = graph.entrypoints[:8]
        core_dirs = graph.core_directories[:6]
        components = []
        for order, directory in enumerate(core_dirs, start=1):
            files = [item.path for item in graph.files if item.path.startswith(f"{directory}/")][:8]
            components.append(
                {
                    "name": directory,
                    "role": self._component_role(directory, files),
                    "audience_note": self._audience_component_note(audience, directory, files),
                    "representative_files": files,
                    "learning_order": order,
                }
            )
        critical_paths = []
        for entry in entrypoints[:4]:
            downstream = [edge.target for edge in graph.imports if edge.source == entry.path][:6]
            tests_for_entry = self._related_tests(graph, entry.path)
            docs_for_entry = self._related_docs(graph, entry.path)
            critical_paths.append(
                {
                    "entrypoint": entry.path,
                    "downstream_dependencies": downstream,
                    "related_tests": tests_for_entry,
                    "related_docs": docs_for_entry,
                    "why_it_matters": self._critical_path_note(audience, entry.path, downstream, tests_for_entry, docs_for_entry),
                }
            )
        uncertainties = []
        if not architecture_doc:
            uncertainties.append("未发现明确的 architecture 文档，架构导览主要来自目录、入口和依赖边。")
        if not graph.imports:
            uncertainties.append("未发现 import edges，关键路径只能基于入口和文件结构低置信推断。")
        return ArchitectureTour(
            repo_id=record.repo_id,
            audience=audience,
            project_goal=self._project_goal(record),
            real_world_problem=self._real_world_problem(record),
            system_pipeline=self._system_pipeline(record),
            major_components=components,
            entry_points=entrypoints,
            key_invariants=self._key_invariants(record) + self._audience_invariants(record, audience),
            critical_paths=critical_paths,
            related_docs=docs[:12],
            related_tests=tests[:12],
            evidence=self._evidence_for_paths(record, self._existing_paths([readme, architecture_doc]) + [item.path for item in entrypoints[:3]], "架构导览"),
            uncertainties=uncertainties,
        )

    def module_study_cards(self, repo_id: str, audience: str = "newcomer", limit: int = 8) -> list[ModuleStudyCard]:
        record = self.repo_store.load(repo_id)
        graph = record.graph
        candidates = self._entry_files(record) + self._core_source_files(record)
        seen: set[str] = set()
        ordered = []
        for path in candidates:
            if path and path not in seen:
                seen.add(path)
                ordered.append(path)
        cards: list[ModuleStudyCard] = []
        for index, path in enumerate(ordered[:limit], start=1):
            symbols = [item.name for item in graph.symbols if item.file_path == path][:10]
            upstream = [edge.source for edge in graph.imports if edge.target == path][:8]
            downstream = [edge.target for edge in graph.imports if edge.source == path][:8]
            tests = self._related_tests(graph, path)
            docs = self._related_docs(graph, path)
            cards.append(
                ModuleStudyCard(
                    module_path=path,
                    role_in_system=self._module_role(path, symbols) + " " + self._audience_module_note(audience, path, tests, docs, upstream, downstream),
                    why_it_exists=self._module_why(path, tests, docs),
                    upstream_callers=upstream,
                    downstream_dependencies=downstream,
                    key_symbols=symbols,
                    related_tests=tests,
                    related_docs=docs,
                    common_change_scenarios=self._change_scenarios(path, tests, docs),
                    risk_if_modified=self._risk_notes_for_file(path, tests, downstream),
                    learning_order=index,
                    audience=audience,
                    evidence=self._evidence_for_paths(record, [path] + tests[:2] + docs[:2], "模块学习卡"),
                    uncertainties=[] if (symbols or tests or docs or upstream or downstream) else ["该模块缺少符号、测试或文档关系，学习卡为低置信。"],
                )
            )
        return cards

    def glossary(self, repo_id: str) -> ProjectGlossary:
        record = self.repo_store.load(repo_id)
        terms: list[ProjectGlossaryTerm] = []
        base_terms = [
            ("entrypoint", "入口文件", "从运行命令进入代码主流程的文件。"),
            ("quality command", "质量命令", "安装、运行、测试、构建、lint 或格式化命令。"),
            ("test edge", "测试关系", "测试文件到被测源码的确定性或启发式映射。"),
            ("doc edge", "文档关系", "文档到源码、符号或命令的 mentions/documents 关系。"),
            ("onboarding debt", "上手债务", "新贡献者入门时缺失的 README、CI、贡献规范、模板或测试入口。"),
        ]
        for term, zh, explanation in base_terms:
            terms.append(
                ProjectGlossaryTerm(
                    term=term,
                    zh_translation=zh,
                    explanation=explanation,
                    source_refs=["RepositoryIntelligenceGraph"],
                    evidence=[self._graph_evidence(record, term, explanation)],
                )
            )
        for directory in record.graph.core_directories[:6]:
            terms.append(
                ProjectGlossaryTerm(
                    term=directory,
                    zh_translation=self._dir_translation(directory),
                    category="module",
                    explanation=f"{directory} 是图谱识别出的核心目录之一，阅读时应结合其中源码、测试和文档边。",
                    source_refs=[directory],
                    evidence=self._evidence_for_paths(record, [self._first_file_in_dir(record, directory)], "术语表：核心目录"),
                )
            )
        for symbol in record.graph.symbols[:12]:
            terms.append(
                ProjectGlossaryTerm(
                    term=symbol.name,
                    zh_translation=f"符号：{symbol.name}",
                    category="symbol",
                    explanation=f"{symbol.name} 是图谱在 {symbol.file_path} 中解析到的 {symbol.symbol_type.value}，中文导读中必须保留原始标识符。",
                    source_refs=[symbol.file_path],
                    evidence=self._evidence_for_paths(record, [symbol.file_path], "术语表：符号名"),
                )
            )
        for concept in self._domain_concepts(record)[:10]:
            terms.append(
                ProjectGlossaryTerm(
                    term=concept["term"],
                    zh_translation=concept["zh"],
                    category="domain",
                    explanation=concept["explanation"],
                    source_refs=concept["sources"],
                    evidence=self._evidence_for_paths(record, concept["sources"], "术语表：领域概念"),
                )
            )
        canonical = []
        if self._find_existing_file(record, ["README_CN.md", "README.zh.md", "README_zh.md"]):
            canonical.append("发现中文 README，可作为中文术语对齐来源。")
        return ProjectGlossary(
            repo_id=record.repo_id,
            terms=terms,
            translation_policy=[
                "不翻译文件路径、命令、URL、类名、函数名和包名。",
                "代码块原样保留；中文只做导读和术语解释。",
                "如果缺少人工中文文档，标记 fidelity warning。",
            ],
            canonical_sources=canonical,
            fidelity_warnings=[] if canonical else ["未发现 README_CN/README.zh 等人工中文文档；当前为确定性中文导读，不等同人工校对全文翻译。"],
        )

    def bilingual_doc_view(self, repo_id: str, source_path: str = "") -> BilingualDocView:
        record = self.repo_store.load(repo_id)
        source = source_path or self._preferred_readme(record) or (self._doc_paths(record)[0] if self._doc_paths(record) else "")
        glossary = self.glossary(repo_id)
        chunks: list[TranslationChunkRecord] = []
        if source:
            text = self._read_text(record, source) or self._file_preview(record, source)
            parts = self._doc_chunks(text)
            commit_hash = self._source_commit_hash(record)
            for index, part in enumerate(parts[:6], start=1):
                tokens = self._preserved_tokens(part)
                translated_text = self._zh_doc_guide(part, tokens)
                glossary_terms = self._glossary_terms_for_chunk(glossary, part)
                chunks.append(
                    TranslationChunkRecord(
                        chunk_id=f"{source}#chunk-{index}",
                        source_file=source,
                        source_chunk_hash=self._chunk_hash(part),
                        source_commit_hash=commit_hash,
                        source_path=source,
                        source_text=part,
                        target_lang="zh-CN",
                        translated_text=translated_text,
                        zh_text=translated_text,
                        glossary_terms=glossary_terms,
                        preserved_tokens=tokens,
                        fidelity_status="deterministic_preserve_tokens",
                        stale_status="fresh" if commit_hash else "unknown_commit",
                        warnings=[] if tokens else ["该片段未识别到需要保护的路径、命令、URL 或代码 token。"],
                        evidence=self._evidence_for_paths(record, [source], "双语导读"),
                    )
                )
        canonical_source = "existing_zh_doc" if glossary.canonical_sources else "deterministic_bilingual_guide"
        return BilingualDocView(
            repo_id=record.repo_id,
            source_path=source,
            canonical_source=canonical_source,
            chunks=chunks,
            glossary=glossary,
            fidelity_warnings=glossary.fidelity_warnings,
        )

    def learning_check(self, repo_id: str, request: LearningCheckRequest) -> LearningCheckResponse:
        record = self.repo_store.load(repo_id)
        answer = request.learner_answer.strip()
        answer_lc = answer.lower()
        key_points = self._learning_check_points(record)
        missing = [point for point, tokens in key_points.items() if not any(token.lower() in answer_lc for token in tokens)]
        evidence = self._evidence_for_paths(record, self._existing_paths([self._preferred_readme(record), *self._entry_files(record)[:1], *self._test_files(record)[:1]]), "学习检查")
        if not answer:
            feedback = "还没有收到你的回答。请先用自己的话说明项目目标、启动命令、入口文件和测试边界。"
            mastery = "low"
        elif len(missing) <= 1:
            feedback = "回答已经覆盖主要事实；请继续把结论绑定到具体文件、命令或测试证据。"
            mastery = "high"
        elif len(missing) <= 3:
            feedback = "回答有基础，但还缺少若干可验证事实；建议补充入口文件、测试命令或文档来源。"
            mastery = "medium"
        else:
            feedback = "回答目前偏概括，缺少来自仓库图谱的事实支撑；请按 README、入口文件、测试文件三类证据重写。"
            mastery = "low"
        return LearningCheckResponse(
            learner_answer=answer,
            grounded_feedback=feedback,
            missing_key_points=missing,
            evidence_refs=[item.source_ref for item in evidence],
            mastery_estimate=mastery,
            evidence=evidence,
        )

    def change_impact(self, repo_id: str, request: ChangeImpactRequest) -> ChangeImpactResponse:
        record = self.repo_store.load(repo_id)
        graph = record.graph
        query = request.file_path.strip() or request.symbol.strip()
        target = request.file_path.strip()
        if not target and request.symbol.strip():
            symbol = next((item for item in graph.symbols if item.name == request.symbol.strip()), None)
            target = symbol.file_path if symbol else ""
        if not target:
            target = (self._entry_files(record) or self._core_source_files(record) or [""])[0]
        direct_imports = [edge.target for edge in graph.imports if edge.source == target]
        imported_by = [edge.source for edge in graph.imports if edge.target == target]
        related_tests = self._related_tests(graph, target)
        related_docs = self._related_docs(graph, target)
        must_read = self._dedupe([target] + imported_by[:4] + direct_imports[:4] + related_docs[:4])
        test_commands = self._command_strings([self._preferred_quality_command(record, CommandType.TEST)])
        if not test_commands:
            test_commands = graph.test_commands[:3]
        risk_notes = self._risk_notes_for_file(target, related_tests, direct_imports)
        confidence = ConfidenceLevel.HIGH if target in self._file_path_set(record) else ConfidenceLevel.MEDIUM if related_tests or related_docs else ConfidenceLevel.LOW
        return ChangeImpactResponse(
            query=query or target,
            likely_affected_modules=self._dedupe(direct_imports + imported_by),
            likely_affected_tests=related_tests,
            must_read_before_editing=must_read,
            must_run_commands=test_commands,
            documentation_to_recheck=related_docs,
            risk_notes=risk_notes,
            evidence=self._evidence_for_paths(record, must_read[:5] + related_tests[:3], "改动影响演练"),
            confidence=confidence,
        )

    def contribution_funnel(self, repo_id: str) -> IssueRecommendationResponse:
        record = self.repo_store.load(repo_id)
        if record.snapshot.issues:
            issues = [self._external_issue_card(record, issue) for issue in sorted(record.snapshot.issues, key=lambda item: item.recommendation_score, reverse=True)[:10]]
            return IssueRecommendationResponse(
                issues=issues,
                message="以下为真实 GitHub open issues，排序依据标签、难度和仓库上下文。",
                self_check=SelfCheckReport(passed=True, evidence_coverage=1.0, suggested_action=SuggestedAction.ACCEPT),
            )
        tasks = self._internal_first_tasks(record)
        return IssueRecommendationResponse(
            issues=tasks,
            message="当前仓库没有 open issue，因此这是基于仓库结构生成的入门练习任务；它们不是 GitHub Issue。",
            self_check=SelfCheckReport(
                passed=bool(tasks),
                evidence_coverage=0.75 if tasks else 0.0,
                missing_evidence=["GitHub open issue count is 0"],
                suggested_action=SuggestedAction.ACCEPT if tasks else SuggestedAction.RETRIEVE_MORE,
            ),
        )

    def onboarding_debt(self, repo_id: str) -> OnboardingDebtReport:
        record = self.repo_store.load(repo_id)
        paths = self._file_path_set(record)
        labels = {label.lower() for issue in record.snapshot.issues for label in issue.labels}
        has_readme = bool(self._preferred_readme(record))
        has_architecture = bool(self._find_existing_file(record, ["docs/architecture.md", "architecture.md"]))
        has_contributing = any(Path(path).name.lower().startswith("contributing") for path in paths)
        has_issue_template = any(path.lower().startswith(".github/issue_template") or "issue_template" in path.lower() for path in paths)
        has_pr_template = any(path.lower().startswith(".github/pull_request_template") or "pull_request_template" in path.lower() for path in paths)
        has_ci = bool(record.graph.ci_rules or any(path.lower().startswith(".github/workflows/") for path in paths))
        has_test_entry = bool(record.graph.test_commands or self._test_files(record))
        has_lint_format = bool(record.graph.lint_commands or record.graph.format_commands or record.graph.development_workflow and (record.graph.development_workflow.code_style_rules or record.graph.development_workflow.lint_commands or record.graph.development_workflow.format_commands))
        has_translation = bool(self._find_existing_file(record, ["README_CN.md", "README.zh.md", "README_zh.md"]) or any("zh" in path.lower() or "_cn" in path.lower() for path in paths))
        has_beginner_commands = bool(record.graph.setup_commands and (record.graph.run_commands or record.graph.test_commands))
        risk_map = [
            (has_readme, "缺少 README，新贡献者无法从项目入口理解目标和启动方式。", "补充 README：项目目标、安装、运行、测试和常见问题。"),
            (has_architecture, "缺少架构文档，学习者难以把模块和主流程对应起来。", "补充 docs/architecture.md，说明入口、核心模块和关键数据流。"),
            (has_contributing, "缺少 CONTRIBUTING，贡献流程和提交前检查不明确。", "补充 CONTRIBUTING.md 或在 README 中写明贡献流程。"),
            (has_issue_template, "缺少 Issue 模板，维护者难以收集稳定复现信息。", "添加 .github/ISSUE_TEMPLATE。"),
            (has_pr_template, "缺少 PR 模板，评审前置检查不明确。", "添加 .github/pull_request_template.md。"),
            (has_ci, "缺少 CI，贡献者无法确认远端检查标准。", "添加 GitHub Actions 或在文档中说明 CI/验证方式。"),
            (has_test_entry, "缺少测试入口或测试文件，新人难以验证改动安全性。", "补充测试命令或 tests 目录说明。"),
            (has_lint_format, "缺少 lint/format 说明，代码风格要求不清楚。", "在 README/CONTRIBUTING 中补充 lint 和 format 命令。"),
            (has_translation, "缺少中文或双语支持，中文学习者上手成本较高。", "补充 README_CN 或术语表，保持命令和路径原样。"),
            (has_beginner_commands, "缺少清晰的安装+运行/测试组合，新贡献者很难完成第一轮闭环。", "在 Quick Start 中放置最小可复现命令。"),
        ]
        risks = [risk for ok, risk, _ in risk_map if not ok]
        actions = [action for ok, _, action in risk_map if not ok]
        return OnboardingDebtReport(
            repo_id=record.repo_id,
            has_readme=has_readme,
            has_architecture_doc=has_architecture,
            has_contributing=has_contributing,
            has_issue_template=has_issue_template,
            has_pr_template=has_pr_template,
            has_good_first_issue=any(label in labels for label in {"good first issue", "good-first-issue", "good first"}),
            has_skill_labels=any(label in labels for label in {"docs", "test", "testing", "setup", "beginner", "documentation"}),
            has_ci=has_ci,
            has_test_entry=has_test_entry,
            has_lint_format_doc=has_lint_format,
            has_translation_support=has_translation,
            has_beginner_friendly_commands=has_beginner_commands,
            onboarding_risks=risks,
            recommended_maintainer_actions=actions,
            evidence=self._evidence_for_paths(record, self._existing_paths([self._preferred_readme(record), ".github/workflows", "CONTRIBUTING.md"]), "上手债务报告"),
        )

    def tutorials(self, repo_id: str) -> list[TutorialDraft]:
        record = self.repo_store.load(repo_id)
        setup = self._preferred_quality_command(record, CommandType.SETUP)
        run = self._preferred_run_command(record)
        test = self._preferred_quality_command(record, CommandType.TEST)
        entry = (self._entry_files(record) or [""])[0]
        first_task = (self.contribution_funnel(repo_id).issues or [None])[0]
        quick_steps = [
            self._tutorial_step("安装依赖", setup, self._preferred_readme(record), "先让本地环境具备运行条件。"),
            self._tutorial_step("运行 demo 或主入口", run, entry, "验证 README 中的启动路径是否仍可复现。"),
            self._tutorial_step("运行测试", test, (self._test_files(record) or [""])[0], "确认环境和基础行为边界。"),
        ]
        flow_steps = [
            TutorialStep(
                title="打开入口文件",
                related_file=entry,
                why_matters="入口文件连接运行命令和内部模块。",
                expected_output="能说明入口文件调用或导入了哪些核心模块。",
                screenshot_placeholder="可在 UI 中展示入口文件和 imports 关系。",
                evidence=self._evidence_for_paths(record, [entry], "教程草稿：主流程"),
            ),
            TutorialStep(
                title="对照模块学习卡",
                related_file=(self._core_source_files(record) or [""])[0],
                why_matters="模块学习卡把上游、下游、测试和文档放在同一视图。",
                expected_output="能写出一个核心模块的角色和风险。",
                screenshot_placeholder="可在 UI 中展示 Module Study Card。",
                evidence=self._evidence_for_paths(record, self._core_source_files(record)[:1], "教程草稿：模块卡"),
            ),
        ]
        contribution_steps = []
        if first_task:
            for step in first_task.suggested_first_steps[:4]:
                contribution_steps.append(
                    TutorialStep(
                        title=step,
                        related_file=(first_task.evidence[0].file_path if first_task.evidence else ""),
                        why_matters=first_task.why_this_is_a_good_first_step or first_task.recommendation_reason,
                        expected_output=first_task.expected_output,
                        screenshot_placeholder="可在 UI 中展示推荐任务和证据来源。",
                        evidence=first_task.evidence,
                    )
                )
        return [
            TutorialDraft(tutorial_id="quick-start", title="Quick Start Tutorial", steps=[step for step in quick_steps if step.command or step.related_file], uncertainties=[]),
            TutorialDraft(tutorial_id="read-main-flow", title="Read Main Flow Tutorial", steps=[step for step in flow_steps if step.related_file], uncertainties=[] if entry else ["未发现入口文件，主流程教程为低置信。"]),
            TutorialDraft(tutorial_id="first-contribution-rehearsal", title="First Contribution Rehearsal Tutorial", steps=contribution_steps, uncertainties=[] if contribution_steps else ["未生成入门任务。"]),
        ]

    def debug_bundle(self, repo_id: str) -> LearningAgentDebugBundle:
        return LearningAgentDebugBundle(
            repo_id=repo_id,
            learning_path_v2=self.learning_path_v2(repo_id),
            architecture_tour=self.architecture_tour(repo_id),
            module_study_cards=self.module_study_cards(repo_id),
            glossary=self.glossary(repo_id),
            bilingual_docs=self.bilingual_doc_view(repo_id),
            contribution_funnel=self.contribution_funnel(repo_id),
            onboarding_debt=self.onboarding_debt(repo_id),
            tutorials=self.tutorials(repo_id),
        )

    def _step(
        self,
        step_id: str,
        title: str,
        goal: str,
        why_now: str,
        prerequisite_concepts: list[str],
        concrete_files: list[str],
        concrete_commands: list[str],
        expected_observations: list[str],
        worked_example: str,
        self_check_questions: list[str],
        common_mistakes: list[str],
        evidence: list[EvidenceItem],
        uncertainties: list[str],
    ) -> LearningPathStepV2:
        return LearningPathStepV2(
            step_id=step_id,
            title=title,
            goal=goal,
            why_now=why_now,
            prerequisite_concepts=prerequisite_concepts,
            concrete_files=self._dedupe([item for item in concrete_files if item]),
            concrete_commands=self._dedupe([item for item in concrete_commands if item]),
            expected_observations=expected_observations,
            worked_example=worked_example,
            self_check_questions=self_check_questions,
            common_mistakes=common_mistakes,
            evidence=evidence[:8],
            uncertainties=uncertainties,
        )

    def _internal_first_tasks(self, record: RepositoryRecord) -> list[IssueRecommendation]:
        tasks: list[IssueRecommendation] = []
        test_command = self._preferred_quality_command(record, CommandType.TEST)
        run_command = self._preferred_run_command(record)
        setup_command = self._preferred_quality_command(record, CommandType.SETUP)
        readme = self._preferred_readme(record)
        architecture_doc = self._find_existing_file(record, ["docs/architecture.md", "architecture.md"])
        entry = (self._entry_files(record) or self._core_source_files(record) or [""])[0]
        safety_test = self._find_existing_file(record, ["tests/test_safety_contract.py"]) or (self._test_files(record) or [""])[0]
        recipes = [
            {
                "enabled": bool(test_command or self._test_files(record)),
                "title": f"跑通 {test_command.command if test_command else '测试命令'}",
                "task_type": "tests",
                "difficulty": "easy",
                "tags": ["test", "setup"],
                "why": "仓库已有测试文件或测试命令，先跑通测试能建立行为边界。",
                "expected": "记录测试是否通过、失败依赖和复现环境。",
                "steps": [f"运行：{test_command.command}" if test_command else "打开 tests 目录确认测试入口", "记录失败输出和依赖版本", "把结果整理成可复现笔记"],
                "files": self._test_files(record)[:2],
                "commands": [test_command] if test_command else [],
            },
            {
                "enabled": bool(architecture_doc and entry),
                "title": f"阅读 {architecture_doc or '架构文档'} 并对照 {entry or '入口源码'}",
                "task_type": "architecture-validation",
                "difficulty": "easy",
                "tags": ["docs", "code-reading"],
                "why": "架构文档和入口源码同时存在，适合做低风险的结构核对任务。",
                "expected": "写出文档中的模块如何对应到源码文件。",
                "steps": [f"阅读 {architecture_doc}", f"打开 {entry}", "列出文档模块和源码模块的一一对应关系"],
                "files": self._existing_paths([architecture_doc, entry]),
                "commands": [],
            },
            {
                "enabled": bool(run_command),
                "title": f"运行 {run_command.command if run_command else 'demo 脚本'}",
                "task_type": "setup",
                "difficulty": "easy",
                "tags": ["setup"],
                "why": "仓库图谱发现了可运行命令，适合验证 Quick Start 是否仍可复现。",
                "expected": "获得 demo 输出或明确的失败条件。",
                "steps": self._dedupe([f"先运行：{setup_command.command}" if setup_command else "", f"再运行：{run_command.command}" if run_command else "", "记录输出、耗时和失败信息"]),
                "files": self._existing_paths([readme, entry]),
                "commands": [item for item in [setup_command, run_command] if item],
            },
            {
                "enabled": bool(readme and (setup_command or run_command or test_command)),
                "title": "检查 README quick start 命令是否能复现",
                "task_type": "docs",
                "difficulty": "easy",
                "tags": ["docs", "setup"],
                "why": "README 与已解析命令可以相互校验，这是维护者最需要的上手反馈。",
                "expected": "形成一份 README 命令复现记录，指出可运行项和失败项。",
                "steps": ["阅读 README 的安装/运行段落", "按顺序执行已解析命令", "记录 README 是否需要更新"],
                "files": self._existing_paths([readme]),
                "commands": [item for item in [setup_command, run_command, test_command] if item],
            },
            {
                "enabled": bool(safety_test),
                "title": f"阅读 {safety_test} 理解测试约束",
                "task_type": "code-reading",
                "difficulty": "medium",
                "tags": ["test", "code-reading"],
                "why": "测试文件能帮助新人理解哪些行为不能被破坏。",
                "expected": "写出测试保护的行为、相关源码和运行命令。",
                "steps": [f"打开 {safety_test}", "查找对应源码或测试边", "补充一段中文测试说明"],
                "files": self._existing_paths([safety_test]),
                "commands": [test_command] if test_command else [],
            },
        ]
        for index, recipe in enumerate([item for item in recipes if item["enabled"]][:6], start=1):
            files = recipe["files"]
            commands = recipe["commands"]
            evidence = self._evidence_for_paths(record, files, "internal first task") + self._command_evidence(record, commands)
            tasks.append(
                IssueRecommendation(
                    issue_number=-index,
                    title=str(recipe["title"]),
                    labels=[],
                    difficulty=str(recipe["difficulty"]),
                    skill_tags=list(recipe["tags"]),
                    recommendation_reason=f"{recipe['why']} 当前仓库没有 open issue，因此这是基于仓库结构生成的入门练习任务。",
                    suggested_first_steps=list(recipe["steps"]),
                    evidence=evidence[:8] or [self._graph_evidence(record, str(recipe["title"]), "internal first task generated from repository graph")],
                    score=0.68 - index * 0.03,
                    source=SourceType.INTERNAL_SUGGESTION.value,
                    confidence=ConfidenceLevel.MEDIUM if evidence else ConfidenceLevel.LOW,
                    is_github_issue=False,
                    task_type=str(recipe["task_type"]),
                    why_this_is_a_good_first_step=str(recipe["why"]),
                    expected_output=str(recipe["expected"]),
                    why_fit_for_beginner=str(recipe["why"]),
                    expected_prerequisites=["能打开仓库文件", "能运行命令行"] if commands else ["能阅读 Markdown 和源码文件"],
                )
            )
        if not tasks:
            evidence = [self._graph_evidence(record, "RepositoryIntelligenceGraph", "fallback internal task")]
            tasks.append(
                IssueRecommendation(
                    issue_number=-1,
                    title="阅读仓库结构并写一份新手导览",
                    difficulty="easy",
                    skill_tags=["docs", "code-reading"],
                    recommendation_reason="当前仓库没有 open issue，且缺少足够命令/测试信息；先整理结构导览是最低风险任务。",
                    suggested_first_steps=["查看文件类型统计", "列出文档、源码、测试、配置文件", "写出一个从 README 到测试命令的最小学习路径"],
                    evidence=evidence,
                    score=0.42,
                    source=SourceType.INTERNAL_SUGGESTION.value,
                    confidence=ConfidenceLevel.LOW,
                    is_github_issue=False,
                    task_type="docs",
                    why_this_is_a_good_first_step="结构导览不改业务代码，适合没有 open issue 时建立贡献上下文。",
                    expected_output="一份新手导览草稿。",
                    why_fit_for_beginner="不需要理解全部业务逻辑，先建立仓库地图。",
                    expected_prerequisites=["能阅读文件树"],
                )
            )
        return tasks

    def _external_issue_card(self, record: RepositoryRecord, issue) -> IssueRecommendation:
        labels = issue.labels or []
        evidence = [
            self.evidence_service.make(
                SourceType.ISSUES,
                f"issue #{issue.issue_number}",
                issue.title,
                "真实 GitHub open issue",
                issue_number=issue.issue_number,
                confidence=0.95,
            )
        ]
        return IssueRecommendation(
            issue_number=issue.issue_number,
            title=issue.title,
            labels=labels,
            difficulty=issue.difficulty if issue.difficulty != "unknown" else "medium",
            skill_tags=issue.skill_tags or self._skill_tags_from_labels(labels),
            recommendation_reason=f"真实 GitHub issue；labels={', '.join(labels) or '无'}；comments={issue.comments_count}。",
            suggested_first_steps=["阅读 issue 描述和最近评论", "定位相关文件或测试", "先提出小范围修改计划并运行相关命令"],
            evidence=evidence,
            score=issue.recommendation_score,
            source="github_issue",
            confidence=ConfidenceLevel.HIGH,
            is_github_issue=True,
            why_fit_for_beginner="基于标签、评论量和难度判断，适合从小范围问题开始。",
            expected_prerequisites=["阅读 issue 上下文", "能运行项目测试"],
        )

    def _tutorial_step(self, title: str, command: QualityCommand | None, related_file: str, why: str) -> TutorialStep:
        return TutorialStep(
            title=title,
            command=command.command if command else "",
            expected_output="命令能运行，或输出明确的缺失依赖/失败原因。" if command else "能定位相关文件。",
            related_file=related_file or "",
            why_matters=why,
            screenshot_placeholder="可在 UI 中展示命令、输出和证据来源。",
            evidence=[],
        )

    def _project_goal(self, record: RepositoryRecord) -> str:
        readme = self._preferred_readme(record)
        text = self._read_text(record, readme) if readme else ""
        title = self._first_heading(text)
        if title:
            return f"基于 {readme}，项目目标应先围绕“{title}”理解，并用后续文档和源码验证。"
        dirs = ", ".join(record.graph.core_directories[:4]) or "已解析源码目录"
        return f"未发现可直接引用的项目标题；请先基于 {dirs} 和 README/文档证据确认项目目标。"

    def _real_world_problem(self, record: RepositoryRecord) -> str:
        if self._preferred_readme(record):
            return "真实问题描述应以 README 的项目简介、Quick Start 和架构文档为准；当前导览只引用已解析文档和文件结构。"
        return "仓库缺少 README，真实问题只能从源码目录和命令低置信推断。"

    def _system_pipeline(self, record: RepositoryRecord) -> list[str]:
        pipeline = []
        setup = self._preferred_quality_command(record, CommandType.SETUP)
        run = self._preferred_run_command(record)
        test = self._preferred_quality_command(record, CommandType.TEST)
        if setup:
            pipeline.append(f"安装依赖：{setup.command}")
        if run:
            pipeline.append(f"进入主流程：{run.command}")
        for entry in self._entry_files(record)[:3]:
            pipeline.append(f"入口文件：{entry}")
        for directory in record.graph.core_directories[:4]:
            pipeline.append(f"核心目录：{directory}")
        if test:
            pipeline.append(f"行为验证：{test.command}")
        return pipeline or ["图谱尚未发现完整 pipeline；请先查看文件树、README 和入口候选。"]

    def _key_invariants(self, record: RepositoryRecord) -> list[str]:
        invariants = [
            "学习结论必须绑定到文件、命令、测试、文档或 issue 证据。",
            "没有被图谱发现的文件、命令和 CI 不应被当成事实展示。",
        ]
        if self._test_files(record):
            invariants.append("修改核心代码前应先查看相关测试并运行测试命令。")
        if record.graph.entrypoints:
            invariants.append("入口文件用于追踪主流程，__init__.py 只能作为包入口或低优先候选。")
        return invariants

    def _component_role(self, directory: str, files: list[str]) -> str:
        text = directory.lower()
        if "test" in text:
            return "测试与行为边界"
        if "doc" in text:
            return "文档与上手材料"
        if "script" in text:
            return "命令行脚本与运行入口"
        if "frontend" in text or "web" in text:
            return "前端页面与交互"
        if "src" in text or files:
            return "主要源码模块"
        return "仓库核心目录"

    def _module_role(self, path: str, symbols: list[str]) -> str:
        name = path.lower()
        if "test" in name:
            return "测试文件，用来描述行为边界。"
        if "script" in name or name.endswith("main.py") or "__main__.py" in name:
            return "运行入口或自动化脚本。"
        if "api" in name:
            return "API 接口层。"
        if "worker" in name or "agent" in name:
            return "Agent/Worker 编排或任务执行模块。"
        if symbols:
            return f"源码模块，包含关键符号：{', '.join(symbols[:4])}。"
        return "源码模块，角色需要结合 imports、测试和文档继续确认。"

    def _module_why(self, path: str, tests: list[str], docs: list[str]) -> str:
        parts = [f"{path} 被图谱识别为需要优先学习的模块。"]
        if tests:
            parts.append("它有相关测试，可从测试理解行为边界。")
        if docs:
            parts.append("它被文档提及，可从文档理解设计意图。")
        return "".join(parts)

    def _change_scenarios(self, path: str, tests: list[str], docs: list[str]) -> list[str]:
        scenarios = ["阅读并补充中文注释或文档说明", "小范围修复前先跑相关测试"]
        if tests:
            scenarios.append("根据测试断言补充边界用例")
        if docs:
            scenarios.append("修改后同步核对相关文档")
        if "script" in path:
            scenarios.append("验证脚本命令仍可复现")
        return scenarios

    def _risk_notes_for_file(self, path: str, tests: list[str], downstream: list[str]) -> list[str]:
        notes = []
        if downstream:
            notes.append("该文件有下游依赖，修改前应查看 imports 影响面。")
        if tests:
            notes.append("存在相关测试，修改后必须运行对应测试或全量测试命令。")
        else:
            notes.append("未发现相关测试边，修改风险较高，需要手动补充验证。")
        if "entry" in path or "main" in path or "script" in path or "__main__.py" in path:
            notes.append("该文件可能位于运行入口附近，修改后应重新跑启动命令。")
        return notes

    def _workflow_uncertainties(self, record: RepositoryRecord) -> list[str]:
        uncertainties = []
        paths = self._file_path_set(record)
        if not any(Path(path).name.lower().startswith("contributing") for path in paths):
            uncertainties.append("未发现 CONTRIBUTING，贡献规则缺失。")
        if not (record.graph.ci_rules or any(path.lower().startswith(".github/workflows/") for path in paths)):
            uncertainties.append("未发现 CI 工作流。")
        if not (record.graph.lint_commands or record.graph.format_commands):
            uncertainties.append("未发现 lint/format 命令。")
        return uncertainties

    def _workflow_files(self, record: RepositoryRecord) -> list[str]:
        paths = self._file_path_set(record)
        candidates = []
        for path in paths:
            lower = path.lower()
            if lower.startswith(".github/") or "contributing" in lower or lower in {"readme.md", "pyproject.toml", "package.json", "requirements.txt", "makefile"}:
                candidates.append(path)
        return sorted(candidates)[:10]

    def _task_related_files(self, tasks: list[IssueRecommendation]) -> list[str]:
        return self._dedupe([ev.file_path for task in tasks for ev in task.evidence if ev.file_path])

    def _task_related_commands(self, tasks: list[IssueRecommendation]) -> list[str]:
        commands = []
        for task in tasks:
            for step in task.suggested_first_steps:
                if "：" in step:
                    command = step.split("：", 1)[1].strip()
                    if command:
                        commands.append(command)
        return self._dedupe(commands)

    def _learning_check_points(self, record: RepositoryRecord) -> dict[str, list[str]]:
        points = {"项目目标缺少文档证据": ["readme", "项目", "目标", "problem", "goal"]}
        entry_files = self._entry_files(record)
        if entry_files:
            points["缺少入口文件"] = entry_files[:3] + ["入口", "entrypoint"]
        run = self._preferred_run_command(record)
        if run:
            points["缺少启动命令"] = [run.command, "启动", "运行"]
        test = self._preferred_quality_command(record, CommandType.TEST)
        if test:
            points["缺少测试边界"] = [test.command, "测试", "pytest"]
        return points

    def _preferred_readme(self, record: RepositoryRecord) -> str:
        paths = self._file_path_set(record)
        for name in ["README.md", "readme.md", "README_CN.md", "README_EN.md"]:
            if name in paths:
                return name
        return next((path for path in paths if Path(path).name.lower().startswith("readme")), "")

    def _find_existing_file(self, record: RepositoryRecord, candidates: list[str]) -> str:
        paths = self._file_path_set(record)
        for candidate in candidates:
            if candidate in paths:
                return candidate
        lowered = {path.lower(): path for path in paths}
        for candidate in candidates:
            found = lowered.get(candidate.lower())
            if found:
                return found
        return ""

    def _entry_files(self, record: RepositoryRecord) -> list[str]:
        paths = self._file_path_set(record)
        result = []
        for entry in record.graph.entrypoints:
            if entry.path in paths and Path(entry.path).name != "__init__.py":
                result.append(entry.path)
        return self._dedupe(result)

    def _core_source_files(self, record: RepositoryRecord) -> list[str]:
        files = []
        entry_paths = set(self._entry_files(record))
        for item in record.graph.files:
            if item.path in entry_paths:
                continue
            if item.file_type.value.startswith("source") and Path(item.path).name != "__init__.py":
                files.append(item.path)
        files.sort(key=lambda path: (0 if path.startswith("src/") else 1, path.count("/"), path))
        return files

    def _test_files(self, record: RepositoryRecord) -> list[str]:
        return [item.path for item in record.graph.files if item.file_type.value == "test"]

    def _doc_paths(self, record: RepositoryRecord) -> list[str]:
        return [item.path for item in record.graph.docs]

    def _related_tests(self, graph, path: str) -> list[str]:
        return self._dedupe([edge.source for edge in graph.tests if edge.target == path] + [edge.target for edge in graph.tests if edge.source == path])

    def _related_docs(self, graph, path: str) -> list[str]:
        docs = []
        for edge in graph.edges:
            if edge.edge_type in {EdgeType.DOCUMENTS, EdgeType.MENTIONS}:
                if edge.target == path:
                    docs.append(edge.source)
                if edge.source == path:
                    docs.append(edge.target)
        return self._dedupe(docs)

    def _quality_commands(self, record: RepositoryRecord) -> list[QualityCommand]:
        commands = list(record.graph.quality_commands)
        synthetic = []
        groups = [
            (record.graph.setup_commands, CommandType.SETUP),
            (record.graph.run_commands, CommandType.DEV),
            (record.graph.test_commands, CommandType.TEST),
            (record.graph.build_commands, CommandType.BUILD),
            (record.graph.lint_commands, CommandType.LINT),
            (record.graph.format_commands, CommandType.FORMAT),
            (record.graph.type_check_commands, CommandType.TYPE_CHECK),
        ]
        for values, command_type in groups:
            for command in values:
                synthetic.append(
                    QualityCommand(
                        name=command.split()[0] if command.split() else command_type.value,
                        command=self._normalize_command(command),
                        command_type=command_type,
                        source_file="RepositoryIntelligenceGraph",
                        confidence=ConfidenceLevel.MEDIUM,
                        evidence_sources=["RepositoryIntelligenceGraph"],
                    )
                )
        return self._dedupe_quality_commands(commands + synthetic)

    def _preferred_quality_command(self, record: RepositoryRecord, command_type: CommandType) -> QualityCommand | None:
        commands = [item for item in self._quality_commands(record) if item.command_type == command_type]
        if not commands:
            return None
        preferences = {
            CommandType.SETUP: ["pip install -r requirements.txt", "npm install", "pnpm install"],
            CommandType.DEV: ["python scripts/run_demo.py", "npm run dev", "python -m"],
            CommandType.TEST: ["python -m pytest tests", "pytest", "npm test"],
        }.get(command_type, [])
        for pattern in preferences:
            for command in commands:
                if self._normalize_command(pattern) in command.command:
                    return command
        return commands[0]

    def _preferred_run_command(self, record: RepositoryRecord) -> QualityCommand | None:
        dev_commands = [item for item in self._quality_commands(record) if item.command_type == CommandType.DEV]
        if not dev_commands:
            return self._preferred_quality_command(record, CommandType.DEV)
        evaluation = re.compile(r"run_(academic_)?eval|run_local_validation|run_stress_test|stress|benchmark", re.I)
        main = [command for command in dev_commands if not evaluation.search(command.command)]
        for preferred in ["python scripts/run_demo.py", "npm run dev", "python -m"]:
            for command in main:
                if preferred in command.command:
                    return command
        return (main or dev_commands)[0]

    def _dedupe_quality_commands(self, commands: list[QualityCommand]) -> list[QualityCommand]:
        rank = {ConfidenceLevel.LOW: 1, ConfidenceLevel.MEDIUM: 2, ConfidenceLevel.HIGH: 3}
        seen: dict[tuple[str, str], QualityCommand] = {}
        for item in commands:
            normalized = self._normalize_command(item.command)
            if not normalized:
                continue
            item.command = normalized
            item.source_file = item.source_file.replace("\\", "/")
            item.evidence_sources = self._dedupe([source.replace("\\", "/") for source in (item.evidence_sources or []) + [item.source_file] if source])
            key = (item.command_type.value, normalized)
            existing = seen.get(key)
            if not existing:
                seen[key] = item
                continue
            existing.evidence_sources = self._dedupe(existing.evidence_sources + item.evidence_sources)
            if rank.get(item.confidence, 0) > rank.get(existing.confidence, 0):
                item.evidence_sources = existing.evidence_sources
                seen[key] = item
        return list(seen.values())

    def _command_strings(self, commands: list[QualityCommand | None]) -> list[str]:
        return self._dedupe([command.command for command in commands if command])

    def _command_evidence(self, record: RepositoryRecord, commands: list[QualityCommand | None]) -> list[EvidenceItem]:
        evidence = []
        for command in commands:
            if not command:
                continue
            source_ref = command.source_file or "RepositoryIntelligenceGraph"
            evidence.append(
                self.evidence_service.make(
                    SourceType.COMMAND,
                    source_ref,
                    command.command,
                    "命令来自确定性仓库解析",
                    file_path=source_ref if source_ref in self._file_path_set(record) else "",
                    confidence={"high": 0.9, "medium": 0.75, "low": 0.55}.get(command.confidence.value, 0.7),
                )
            )
        return evidence

    def _evidence_for_paths(self, record: RepositoryRecord, paths: list[str], claim: str) -> list[EvidenceItem]:
        evidence = []
        for path in self._dedupe([item for item in paths if item])[:8]:
            if path not in self._file_path_set(record):
                continue
            node = next((item for item in record.graph.files if item.path == path), None)
            source_type = SourceType.CODE
            if node and node.file_type.value.startswith("docs"):
                source_type = SourceType.DOCS
            elif node and node.file_type.value == "test":
                source_type = SourceType.TEST
            elif node and node.file_type.value in {"config", "build"}:
                source_type = SourceType.CONFIG if node.file_type.value == "config" else SourceType.BUILD
            quote = self._file_preview(record, path) or path
            evidence.append(
                self.evidence_service.make(
                    source_type,
                    path,
                    quote,
                    claim,
                    file_path=path,
                    confidence=0.85,
                )
            )
        return evidence

    def _graph_evidence(self, record: RepositoryRecord, source_ref: str, claim: str) -> EvidenceItem:
        quote = f"files={len(record.graph.files)}, symbols={len(record.graph.symbols)}, tests={len(record.graph.tests)}, docs={len(record.graph.docs)}"
        return self.evidence_service.make(SourceType.GRAPH, source_ref, quote, claim, confidence=0.8)

    def _existing_paths(self, paths: list[str]) -> list[str]:
        return self._dedupe([item for item in paths if item])

    def _file_path_set(self, record: RepositoryRecord) -> set[str]:
        return {item.path for item in record.graph.files}

    def _file_preview(self, record: RepositoryRecord, path: str) -> str:
        node = next((item for item in record.graph.files if item.path == path), None)
        return (node.content_preview if node else "")[:600]

    def _read_text(self, record: RepositoryRecord, path: str, limit: int = 12000) -> str:
        if not path:
            return ""
        root = Path(record.snapshot.local_path or "")
        full_path = root / path
        try:
            if full_path.exists() and full_path.is_file():
                return full_path.read_text(encoding="utf-8", errors="ignore")[:limit]
        except OSError:
            return ""
        return self._file_preview(record, path)

    def _first_heading(self, text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip().lstrip("\ufeff")
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()
        return ""

    def _doc_chunks(self, text: str) -> list[str]:
        if not text:
            return []
        parts = re.split(r"\n(?=##?\s+)", text)
        if len(parts) <= 1:
            parts = [text[i : i + 900] for i in range(0, min(len(text), 4500), 900)]
        return [part.strip()[:1200] for part in parts if part.strip()]

    def _preserved_tokens(self, text: str) -> list[str]:
        patterns = [
            r"`([^`]+)`",
            r"https?://[^\s)]+",
            r"(?:[\w.-]+/)+[\w.-]+\.\w+",
            r"\b(?:python|pip|pytest|npm|pnpm|yarn|uvicorn|ruff|black|mypy|make)\s+[^\n]+",
        ]
        tokens: list[str] = []
        for pattern in patterns:
            for match in re.findall(pattern, text):
                token = match if isinstance(match, str) else match[0]
                token = token.strip()
                if token:
                    tokens.append(token)
        return self._dedupe(tokens)[:20]

    def _zh_doc_guide(self, text: str, tokens: list[str]) -> str:
        heading = self._first_heading(text)
        lines = ["中文导读：这段文档应按原文事实理解，代码、路径、命令和链接保持原样。"]
        if heading:
            lines.append(f"本段主题：{heading}")
        if tokens:
            lines.append("需要原样保留的 token：" + "、".join(tokens[:8]))
        lines.append("原文片段保留如下：")
        lines.append(text[:900])
        return "\n".join(lines)

    def _worked_example(self, text: str, files: list[str], commands: list[str] | None = None) -> str:
        parts = [text]
        if files:
            parts.append("示例文件：" + "、".join(files[:4]))
        if commands:
            parts.append("示例命令：" + "、".join(commands[:4]))
        return " ".join(parts)

    def _normalize_command(self, command: str) -> str:
        return " ".join(str(command or "").replace("\\", "/").strip().split())

    def _dedupe(self, values: list[str]) -> list[str]:
        result = []
        seen = set()
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    def _skill_tags_from_labels(self, labels: list[str]) -> list[str]:
        text = " ".join(labels).lower()
        tags = []
        if "doc" in text:
            tags.append("docs")
        if "test" in text:
            tags.append("test")
        if "setup" in text or "install" in text:
            tags.append("setup")
        if "bug" in text:
            tags.append("code-reading")
        return tags or ["code-reading"]

    def _first_file_in_dir(self, record: RepositoryRecord, directory: str) -> str:
        return next((item.path for item in record.graph.files if item.path.startswith(f"{directory}/")), "")

    def _dir_translation(self, directory: str) -> str:
        mapping = {
            "src": "源码",
            "tests": "测试",
            "docs": "文档",
            "scripts": "脚本",
            "frontend": "前端",
            "backend": "后端",
            "app": "应用",
        }
        return mapping.get(directory.lower(), f"{directory} 模块")

    def _chunk_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]

    def _source_commit_hash(self, record: RepositoryRecord) -> str:
        root = Path(record.snapshot.local_path or "")
        head = root / ".git" / "HEAD"
        try:
            if not head.exists():
                return ""
            ref = head.read_text(encoding="utf-8", errors="ignore").strip()
            if ref.startswith("ref:"):
                ref_path = root / ".git" / ref.split(":", 1)[1].strip()
                return ref_path.read_text(encoding="utf-8", errors="ignore").strip()[:40] if ref_path.exists() else ""
            return ref[:40]
        except OSError:
            return ""

    def _glossary_terms_for_chunk(self, glossary: ProjectGlossary, text: str) -> list[str]:
        lowered = text.lower()
        return [
            term.term
            for term in glossary.terms
            if term.term and term.term.lower() in lowered
        ][:12]

    def _domain_concepts(self, record: RepositoryRecord) -> list[dict[str, object]]:
        concepts: list[dict[str, object]] = []
        for path in self._doc_paths(record)[:6]:
            text = self._read_text(record, path, limit=2500) or self._file_preview(record, path)
            for heading in re.findall(r"^[\ufeff\s]*#{1,3}\s+(.+)$", text, flags=re.MULTILINE):
                clean = re.sub(r"[`*_#]", "", heading).strip()
                if not clean or len(clean) > 80:
                    continue
                concepts.append(
                    {
                        "term": clean,
                        "zh": f"概念：{clean}",
                        "explanation": f"{clean} 来自 {path} 的文档标题，属于项目文档中显式出现的领域概念。",
                        "sources": [path],
                    }
                )
        return concepts

    def _audience_component_note(self, audience: str, directory: str, files: list[str]) -> str:
        if audience == "maintainer":
            return f"维护者视角：检查 {directory} 是否有清晰边界、文档和测试覆盖。"
        if audience == "contributor":
            return f"贡献者视角：先看 {directory} 的代表文件，再找相关测试和可运行命令。"
        return f"新手视角：把 {directory} 当成学习地图中的一个区域，先理解它解决什么问题。"

    def _critical_path_note(self, audience: str, entrypoint: str, downstream: list[str], tests: list[str], docs: list[str]) -> str:
        if audience == "maintainer":
            return f"{entrypoint} 是入口候选；维护时应确认下游依赖、测试覆盖和文档是否同步。"
        if audience == "contributor":
            return f"{entrypoint} 连接运行命令和下游模块，改动前先读相关测试 {', '.join(tests[:3]) or '未发现'}。"
        return f"{entrypoint} 是理解主流程的起点；先看它调用了哪些模块，再回到 README 验证。"

    def _audience_invariants(self, record: RepositoryRecord, audience: str) -> list[str]:
        if audience == "maintainer":
            return [
                "维护者视角需要关注缺失文档、缺失 CI、缺失模板和缺失测试入口。",
                "所有新手建议都应可被 README、命令、测试或文档边验证。",
            ]
        if audience == "contributor":
            return [
                "贡献者视角需要把每次改动映射到必读文件、必跑命令和相关测试。",
            ]
        return [
            "新手视角优先减少术语密度，先建立项目目标、入口和测试边界。",
        ]

    def _audience_module_note(
        self,
        audience: str,
        path: str,
        tests: list[str],
        docs: list[str],
        upstream: list[str],
        downstream: list[str],
    ) -> str:
        if audience == "maintainer":
            return f"维护者重点：边界={len(upstream)} 个上游/{len(downstream)} 个下游，文档={len(docs)}，测试={len(tests)}。"
        if audience == "contributor":
            return f"贡献者重点：改 {path} 前先读相关测试和文档，低置信关系要手动验证。"
        return "新手重点：先用一句话说清它在主流程里的作用，再看测试确认行为边界。"

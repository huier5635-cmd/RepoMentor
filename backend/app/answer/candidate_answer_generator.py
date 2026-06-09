from __future__ import annotations

from collections import Counter

from app.answer.evidence_builder import EvidenceBuilder
from app.core.schemas import AnswerBundle, CommandType, EvidenceItem, QualityCommand, RepositoryIntelligenceGraph, SharedWorkingMemory, TaskType


class CandidateAnswerGenerator:
    def __init__(self) -> None:
        self.evidence_builder = EvidenceBuilder()

    def generate(
        self,
        task_type: TaskType,
        memory: SharedWorkingMemory,
        graph: RepositoryIntelligenceGraph,
    ) -> AnswerBundle:
        evidence = self._dedupe_evidence(
            memory.retrieved_evidence + [item for output in memory.worker_outputs for item in output.evidence]
        )
        structured_evidence = self.evidence_builder.build_for_task(task_type, memory.user_question, graph, memory.worker_outputs)
        evidence = self._dedupe_evidence(evidence + structured_evidence)
        question = memory.user_question or ""
        if task_type == TaskType.SETUP_RUN:
            return self._setup_answer(evidence, graph)
        if task_type == TaskType.LEARNING_PATH:
            return self._learning_answer(evidence, graph)
        if task_type == TaskType.ISSUE_RECOMMENDATION:
            return self._issue_answer(evidence, graph)
        if task_type == TaskType.TEST_MAPPING:
            return self._test_mapping_answer(evidence, graph, memory.user_question)
        if self._is_entrypoint_question(question):
            return self._entrypoints_answer(evidence, graph)
        if self._is_docs_question(question):
            return self._docs_recommendation_answer(evidence, graph)
        if self._is_beginner_task_question(question):
            return self._issue_answer(evidence, graph)
        if self._is_core_modules_question(question):
            return self._core_modules_answer(evidence, graph)
        if task_type == TaskType.CODE_EXPLANATION:
            return self._code_answer(evidence, memory)
        if task_type == TaskType.DEVELOPMENT_WORKFLOW:
            return self._development_workflow_answer(evidence, graph)
        return self._overview_answer(evidence, graph)

    def _setup_answer(self, evidence: list[EvidenceItem], graph: RepositoryIntelligenceGraph) -> AnswerBundle:
        commands = self._quality_commands(graph)
        if not evidence and not commands:
            return self._insufficient("当前证据不足：没有检索到 README 或已解析命令中的启动/测试命令。")
        setup_commands = self._commands_by_type(commands, CommandType.SETUP)
        run_commands = self._commands_by_type(commands, CommandType.DEV)
        test_commands = self._commands_by_type(commands, CommandType.TEST)
        build_commands = self._commands_by_type(commands, CommandType.BUILD)

        install = self._pick(setup_commands, ["pip install -r requirements.txt", "pip install -e ."]) or setup_commands[:1]
        demo = self._pick(run_commands, ["python scripts/run_demo.py"]) or [
            command for command in run_commands if "run_demo.py" in command.command
        ][:1]
        demo_optional = [
            command for command in run_commands
            if "run_demo.py" in command.command and command.command not in {item.command for item in demo}
        ]
        evaluation = [
            command for command in run_commands + test_commands + build_commands
            if any(token in command.command for token in ["run_academic_eval.py", "run_eval.py", "run_local_validation.py", "run_stress_test.py"])
        ]
        tests = self._pick(test_commands, ["python -m pytest tests", "pytest"]) or [
            command for command in test_commands if "pytest" in command.command
        ][:2]
        verifiable = self._dedupe_quality_commands(install + demo + demo_optional + evaluation + tests + build_commands)
        source_refs = self._evidence_refs(evidence, verifiable)
        steps = [
            "1. 推荐启动方式：" + self._format_command_group(install + demo, "暂未检测到明确 demo 启动命令，请先阅读 README。"),
            "2. 可选 demo 命令：" + self._format_command_group(demo_optional, "暂无额外 demo 参数示例。"),
            "3. 评估/高级命令：" + self._format_command_group(evaluation, "暂无评估或高级命令。"),
            "4. 测试命令：" + self._format_command_group(tests, "暂未检测到明确测试命令。"),
            "5. 风险提示：命令来自静态解析，依赖版本、环境变量和系统差异仍需在本地验证。",
            "6. 证据来源：" + ("、".join(source_refs) if source_refs else "README 和已解析命令。"),
        ]
        return AnswerBundle(
            conclusion="这个项目推荐先安装依赖，再运行 demo 脚本。",
            task_type=TaskType.SETUP_RUN,
            answer_type="setup_run",
            evidence=evidence,
            steps=steps,
            risks=["如果本地 Python 版本、依赖版本或环境变量不同，命令仍可能失败；请以 README 和实际终端输出为准。"],
            verifiable_commands=[command.command for command in verifiable],
            confidence=self._confidence(evidence, commands),
            uncertainties=[] if demo else ["未检测到无参数 demo 启动命令"],
        )

    def _learning_answer(self, evidence: list[EvidenceItem], graph: RepositoryIntelligenceGraph) -> AnswerBundle:
        steps = []
        if graph.docs:
            docs = [item.path for item in graph.docs if item.name.lower().startswith("readme")] or [item.path for item in graph.docs[:3]]
            steps.append("先读 README/docs：" + "；".join(docs[:3]))
        if graph.setup_commands or graph.run_commands:
            steps.append("跑通安装和启动命令：" + "；".join((graph.setup_commands + graph.run_commands)[:5]))
        elif any(item.source_type.value == "command" for item in evidence):
            steps.append("跑通 Evidence 中列出的安装/启动命令。")
        if graph.core_directories:
            steps.append("阅读核心目录：" + "；".join(graph.core_directories[:6]))
        if graph.entrypoints:
            steps.append("再看入口文件：" + "；".join(item.path for item in graph.entrypoints[:5]))
        if graph.symbols:
            steps.append("按高频符号和核心模块阅读关键类/函数。")
        if graph.tests:
            steps.append("最后从测试文件反推行为边界和改动验证方式。")
        if graph.development_workflow:
            steps.append("学习开发流程：" + "；".join(graph.development_workflow.new_contributor_checklist[:4]))
        if any(item.source_type.value == "internal_suggestion" for item in evidence):
            steps.append("选择 internal first task：当前无 open issue 时，从测试、README、入口文件或文档练习开始。")
        if not steps:
            return self._insufficient("当前证据不足：仓库结构中没有足够的 docs、entrypoints、symbols 或 tests。")
        return AnswerBundle(
            conclusion="建议按 docs -> entrypoints -> symbols/imports -> tests 的顺序学习这个仓库。",
            task_type=TaskType.LEARNING_PATH,
            answer_type="learning_path",
            evidence=evidence,
            steps=steps,
            risks=["学习路径是基于静态结构生成的，不能替代实际运行项目后的行为观察。"],
            verifiable_commands=graph.test_commands,
            confidence=self._confidence(evidence, steps),
            uncertainties=[],
        )

    def _issue_answer(self, evidence: list[EvidenceItem], graph: RepositoryIntelligenceGraph) -> AnswerBundle:
        if not evidence:
            return self._insufficient("当前证据不足：没有可引用的真实 GitHub Issue。")
        internal = [item for item in evidence if item.source_type.value == "internal_suggestion"]
        if internal:
            steps = []
            if graph.test_commands:
                steps.append("不是 GitHub Issue：先跑通测试命令：" + "；".join(graph.test_commands[:3]))
            if graph.entrypoints:
                steps.append("不是 GitHub Issue：阅读入口文件：" + "；".join(item.path for item in graph.entrypoints[:3]))
            docs = [item for item in graph.docs if item.name.lower().startswith("readme") or "architecture" in item.path.lower()]
            if docs:
                steps.append("不是 GitHub Issue：先读文档：" + "；".join(item.path for item in docs[:3]))
            if not steps:
                steps.append("不是 GitHub Issue：基于 RepositoryGraph 写一份新手导览。")
            return AnswerBundle(
                conclusion="当前仓库没有 open issue，因此这些是基于仓库结构生成的入门练习任务。",
                task_type=TaskType.ISSUE_RECOMMENDATION,
                answer_type="beginner_tasks",
                evidence=evidence,
                steps=steps,
                risks=["这些任务不是 GitHub Issue；开始前仍需检查 README 和当前仓库状态。"],
                verifiable_commands=graph.test_commands[:3],
                confidence=self._confidence(evidence, steps),
                uncertainties=[],
            )
        return AnswerBundle(
            conclusion="Issue 推荐必须引用真实 issue，并综合 labels、活跃度、范围、测试/文档信号和技能标签。",
            task_type=TaskType.ISSUE_RECOMMENDATION,
            answer_type="issue_recommendation",
            evidence=evidence,
            steps=["优先选择范围小、描述清晰、评论较少、带 docs/test/good first/help wanted 信号的 issue。"],
            risks=["GitHub API 可能返回不完整；推荐结果需要打开 issue 页面核对最新讨论。"],
            verifiable_commands=[],
            confidence=self._confidence(evidence, []),
        )

    def _test_mapping_answer(self, evidence: list[EvidenceItem], graph: RepositoryIntelligenceGraph, question: str) -> AnswerBundle:
        commands = graph.test_commands or ["pytest", "npm test"]
        related_edges = [edge for edge in graph.tests if edge.source.lower() in question.lower() or edge.target.lower() in question.lower()]
        steps = [f"优先运行相关测试：{edge.source}" for edge in related_edges[:5]]
        steps.append("再运行仓库级测试命令：" + "；".join(commands))
        return AnswerBundle(
            conclusion="测试映射来自测试文件命名规则和 Repository Intelligence Graph 中的 tests 边。",
            task_type=TaskType.TEST_MAPPING,
            answer_type="test_mapping",
            evidence=evidence,
            steps=steps,
            risks=["当前 tests 边是启发式映射，覆盖率数据接入前不能保证完整。"],
            verifiable_commands=commands,
            confidence=self._confidence(evidence, related_edges),
            uncertainties=[] if related_edges else ["没有找到直接命名匹配的测试文件"],
        )

    def _code_answer(self, evidence: list[EvidenceItem], memory: SharedWorkingMemory) -> AnswerBundle:
        findings = [finding for output in memory.worker_outputs for finding in output.findings]
        if not evidence:
            return self._insufficient("当前证据不足：没有找到与目标模块/函数直接匹配的 symbol、import、test 或 docs 证据。")
        return AnswerBundle(
            conclusion="代码解释基于已解析的 symbols、imports、tests/docs 证据生成。",
            task_type=TaskType.CODE_EXPLANATION,
            answer_type="code_explanation",
            evidence=evidence,
            steps=findings[:8] or ["阅读引用的 symbol 和 import 证据，再查看关联测试。"],
            risks=["JS/TS 首版解析使用规则匹配，复杂语法可能漏掉部分符号或依赖。"],
            verifiable_commands=[],
            confidence=self._confidence(evidence, findings),
            uncertainties=memory.unresolved_uncertainties,
        )

    def _development_workflow_answer(self, evidence: list[EvidenceItem], graph: RepositoryIntelligenceGraph) -> AnswerBundle:
        guide = graph.development_workflow
        if guide is None:
            return self._insufficient("当前证据不足：仓库中还没有 Development Workflow Worker 的结构化输出。")

        all_commands = (
            guide.development_commands
            + guide.test_commands
            + guide.lint_commands
            + guide.format_commands
            + guide.type_check_commands
            + guide.build_commands
        )
        steps = [
            "clone / fork 仓库，并阅读 README 与贡献文档。",
            *guide.setup_steps[:5],
        ]
        if guide.test_commands:
            steps.append("运行测试命令：" + "；".join(command.command for command in guide.test_commands[:4]))
        if guide.lint_commands:
            steps.append("运行 lint 命令：" + "；".join(command.command for command in guide.lint_commands[:4]))
        if guide.format_commands:
            steps.append("运行 format 命令：" + "；".join(command.command for command in guide.format_commands[:4]))
        if guide.type_check_commands:
            steps.append("运行类型检查命令：" + "；".join(command.command for command in guide.type_check_commands[:4]))
        steps.extend(guide.contribution_steps[:6])
        if guide.pull_request_rules:
            steps.append("按 PR 模板提交，并附上测试结果、关联 issue 或截图等要求。")

        risks = list(guide.uncertainties)
        if not guide.lint_commands:
            risks.append("没有找到可证据确认的 lint 命令。")
        if not guide.format_commands:
            risks.append("没有找到可证据确认的 format 命令。")
        if not guide.pull_request_rules:
            risks.append("没有找到明确 PR 模板，不能编造 PR 必填项。")

        return AnswerBundle(
            conclusion="这个仓库的新贡献者开发流程应以 Development Workflow Worker 从 README、贡献文档、配置文件和 CI 中抽取的证据为准。",
            task_type=TaskType.DEVELOPMENT_WORKFLOW,
            answer_type="development_workflow",
            evidence=guide.evidence + evidence,
            steps=self._dedupe_strings(steps),
            risks=self._dedupe_strings(risks),
            verifiable_commands=self._dedupe_strings([command.command for command in all_commands]),
            confidence=self._confidence(guide.evidence + evidence, all_commands),
            uncertainties=guide.uncertainties,
        )

    def _overview_answer(self, evidence: list[EvidenceItem], graph: RepositoryIntelligenceGraph) -> AnswerBundle:
        if not evidence and not graph.files:
            return self._insufficient("当前证据不足：没有可用的文档、代码或 issue 证据。")
        docs = [item for item in evidence if item.source_type.value == "docs"]
        graph_evidence = [item for item in evidence if item.source_type.value == "graph"]
        readme_refs = self._dedupe_strings([item.file_path or item.source_ref for item in docs[:4]])
        if readme_refs:
            conclusion = "这个仓库的用途优先依据 README/docs 中的项目介绍，并结合入口文件、符号图和命令结构判断。"
        else:
            conclusion = "这个仓库的用途依据 RepositoryGraph 的文件、符号、入口文件和命令摘要做中低置信判断。"
        return AnswerBundle(
            conclusion=conclusion,
            task_type=TaskType.REPO_OVERVIEW,
            answer_type="overview",
            evidence=evidence,
            steps=[
                "优先查看项目介绍来源：" + ("、".join(readme_refs) if readme_refs else "RepositoryGraph summary"),
                f"查看文档/源码/符号数量：{len(graph.docs)} docs / {len(graph.files)} files / {len(graph.symbols)} symbols",
                "结合 entrypoints、run/test/build commands 验证项目行为。",
            ],
            risks=["如果 README 缺失或过期，概览只能依赖代码结构，置信度会降低。"],
            verifiable_commands=graph.run_commands + graph.test_commands,
            confidence=self._confidence(evidence, graph.files),
            uncertainties=[] if evidence else ["没有检索到可直接引用的 docs/code/issues 证据"],
        )

    def _insufficient(self, conclusion: str) -> AnswerBundle:
        return AnswerBundle(
            conclusion=conclusion,
            task_type=None,
            answer_type="insufficient",
            evidence=[],
            steps=[],
            risks=["证据不足时不输出无来源事实。"],
            verifiable_commands=[],
            confidence=0.2,
            uncertainties=["当前证据不足"],
        )

    def _core_modules_answer(self, evidence: list[EvidenceItem], graph: RepositoryIntelligenceGraph) -> AnswerBundle:
        if not evidence and not graph.symbols:
            return self._insufficient("当前证据不足：没有源码、核心目录或符号证据。")
        symbol_counts = Counter(symbol.file_path for symbol in graph.symbols)
        steps = []
        for directory in graph.core_directories[:6]:
            files_in_dir = [file for file in graph.files if file.path == directory or file.path.startswith(f"{directory}/")]
            steps.append(f"{directory}：核心目录，包含 {len(files_in_dir)} 个文件，建议先看其中源码文件。")
        for file_path, count in symbol_counts.most_common(5):
            steps.append(f"{file_path}：定义 {count} 个已解析符号，可作为核心模块阅读入口。")
        if graph.entrypoints:
            steps.append("入口相关核心文件：" + "；".join(item.path for item in graph.entrypoints[:4]))
        return AnswerBundle(
            conclusion="核心模块来自核心目录、核心源码文件和 symbols summary 的结构化证据。",
            task_type=TaskType.CODE_EXPLANATION,
            answer_type="core_modules",
            evidence=evidence,
            steps=self._dedupe_strings(steps),
            risks=["核心模块排序来自静态文件和符号统计，不能替代运行时调用链分析。"],
            verifiable_commands=graph.test_commands[:3],
            confidence=self._confidence(evidence, graph.symbols),
            uncertainties=[] if graph.symbols else ["仓库没有可解析源码符号。"],
        )

    def _entrypoints_answer(self, evidence: list[EvidenceItem], graph: RepositoryIntelligenceGraph) -> AnswerBundle:
        if not graph.entrypoints:
            return AnswerBundle(
                conclusion="当前没有检测到明确入口文件。",
                task_type=TaskType.CODE_EXPLANATION,
                answer_type="entrypoints",
                evidence=evidence,
                steps=["RepositoryGraph entrypoints 为空；请先看 README 和核心目录。"],
                risks=["入口缺失是结构化不确定性，不应编造 main.py 或 app.py。"],
                confidence=self._confidence(evidence, graph.files),
                uncertainties=["未检测到明确入口文件。"],
            )
        steps = [
            f"{item.path}：{item.reason}；来源：{item.source}；confidence={item.confidence.value}"
            for item in graph.entrypoints[:8]
        ]
        return AnswerBundle(
            conclusion="入口文件来自 RepositoryGraph entrypoints，按置信度和来源排序展示。",
            task_type=TaskType.CODE_EXPLANATION,
            answer_type="entrypoints",
            evidence=evidence,
            steps=steps,
            risks=["low confidence 的 package entry 只表示包入口，不代表主流程入口。"],
            verifiable_commands=graph.run_commands[:4],
            confidence=self._confidence(evidence, graph.entrypoints),
            uncertainties=[item.path for item in graph.entrypoints if item.confidence.value == "low"][:5],
        )

    def _docs_recommendation_answer(self, evidence: list[EvidenceItem], graph: RepositoryIntelligenceGraph) -> AnswerBundle:
        docs = [item for item in graph.docs if item.name.lower().startswith("readme")]
        docs.extend(item for item in graph.docs if item not in docs and any(token in item.path.lower() for token in ["architecture", "quick", "install", "contributing", "testing", "evaluation"]))
        docs.extend(item for item in graph.docs if item not in docs)
        if not evidence and not docs:
            return self._insufficient("当前证据不足：没有 README 或 docs 文档证据。")
        steps = [
            f"{item.path}：{self._doc_reason(item.path)}"
            for item in docs[:8]
        ]
        return AnswerBundle(
            conclusion="文档推荐优先从 README 开始，再看架构、安装/测试、贡献和评估相关文档。",
            task_type=TaskType.GENERAL_QA,
            answer_type="docs_recommendation",
            evidence=evidence,
            steps=steps or ["先从 Evidence 中列出的 README/docs 文档开始。"],
            risks=["文档推荐基于文件名和静态内容预览，仍需打开原文核对最新说明。"],
            verifiable_commands=graph.run_commands[:2] + graph.test_commands[:2],
            confidence=self._confidence(evidence, docs),
            uncertainties=[],
        )

    def _confidence(self, evidence: list[EvidenceItem], support: object) -> float:
        support_count = len(support) if hasattr(support, "__len__") else 0
        return min(0.95, 0.35 + len(evidence) * 0.08 + min(0.2, support_count * 0.02))

    def _dedupe_strings(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            if value and value not in seen:
                result.append(value)
                seen.add(value)
        return result

    def _quality_commands(self, graph: RepositoryIntelligenceGraph) -> list[QualityCommand]:
        commands = list(graph.quality_commands)
        if commands:
            return self._dedupe_quality_commands(commands)
        fallback: list[QualityCommand] = []
        for command in graph.setup_commands:
            fallback.append(QualityCommand(name="setup", command=command, command_type=CommandType.SETUP, source_file="RepositoryIntelligenceGraph"))
        for command in graph.run_commands:
            fallback.append(QualityCommand(name="run", command=command, command_type=CommandType.DEV, source_file="RepositoryIntelligenceGraph"))
        for command in graph.test_commands:
            fallback.append(QualityCommand(name="test", command=command, command_type=CommandType.TEST, source_file="RepositoryIntelligenceGraph"))
        for command in graph.build_commands:
            fallback.append(QualityCommand(name="build", command=command, command_type=CommandType.BUILD, source_file="RepositoryIntelligenceGraph"))
        return self._dedupe_quality_commands(fallback)

    def _commands_by_type(self, commands: list[QualityCommand], command_type: CommandType) -> list[QualityCommand]:
        return [command for command in commands if command.command_type == command_type]

    def _pick(self, commands: list[QualityCommand], preferred: list[str]) -> list[QualityCommand]:
        by_command = {self._normalize_command(command.command): command for command in commands}
        result: list[QualityCommand] = []
        for item in preferred:
            command = by_command.get(self._normalize_command(item))
            if command:
                result.append(command)
        return self._dedupe_quality_commands(result)

    def _format_command_group(self, commands: list[QualityCommand], empty: str) -> str:
        normalized = self._dedupe_quality_commands(commands)
        if not normalized:
            return empty
        return "；".join(command.command for command in normalized)

    def _evidence_refs(self, evidence: list[EvidenceItem], commands: list[QualityCommand]) -> list[str]:
        refs = [item.file_path or item.source_ref for item in evidence if item.file_path or item.source_ref]
        for command in commands:
            refs.extend(command.evidence_sources or [command.source_file])
        return self._dedupe_strings([ref for ref in refs if ref])

    def _dedupe_quality_commands(self, commands: list[QualityCommand]) -> list[QualityCommand]:
        rank = {"low": 1, "medium": 2, "high": 3}
        by_key: dict[tuple[str, str], QualityCommand] = {}
        for command in commands:
            normalized = self._normalize_command(command.command)
            if not normalized:
                continue
            command.command = normalized
            command.source_file = command.source_file.replace("\\", "/")
            sources = set(command.evidence_sources or [])
            if command.source_file:
                sources.add(command.source_file)
            command.evidence_sources = sorted(item.replace("\\", "/") for item in sources if item)
            key = (command.command_type.value, normalized)
            existing = by_key.get(key)
            if existing is None:
                by_key[key] = command
                continue
            existing.evidence_sources = sorted(set(existing.evidence_sources + command.evidence_sources))
            if rank.get(command.confidence.value, 0) > rank.get(existing.confidence.value, 0):
                command.evidence_sources = existing.evidence_sources
                by_key[key] = command
        return list(by_key.values())

    def _normalize_command(self, command: str) -> str:
        return " ".join(command.replace("\\", "/").strip().split())

    def _dedupe_evidence(self, values: list[EvidenceItem]) -> list[EvidenceItem]:
        seen: set[str] = set()
        result: list[EvidenceItem] = []
        for item in values:
            if item.evidence_id in seen:
                continue
            result.append(item)
            seen.add(item.evidence_id)
        return result

    def _is_entrypoint_question(self, question: str) -> bool:
        return any(token in question.lower() for token in ["入口", "entrypoint", "entry point", "main file"])

    def _is_core_modules_question(self, question: str) -> bool:
        return any(token in question.lower() for token in ["核心模块", "核心目录", "核心文件", "主要模块", "core module"])

    def _is_docs_question(self, question: str) -> bool:
        return any(token in question.lower() for token in ["文档", "docs", "readme", "先看"])

    def _is_beginner_task_question(self, question: str) -> bool:
        return any(token in question.lower() for token in ["新手", "入门任务", "适合", "good first", "beginner"])

    def _doc_reason(self, path: str) -> str:
        lowered = path.lower()
        if "readme" in lowered:
            return "项目目标、安装和使用入口。"
        if "architecture" in lowered:
            return "理解架构模块和源码对应关系。"
        if "contributing" in lowered:
            return "了解贡献流程和约束。"
        if "test" in lowered or "testing" in lowered:
            return "了解测试和验证方式。"
        if "eval" in lowered or "evaluation" in lowered:
            return "了解评估或高级命令。"
        return "补充项目背景和实现细节。"

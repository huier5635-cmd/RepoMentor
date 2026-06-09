from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.core.schemas import (
    ChunkDoc,
    CIRule,
    CommandType,
    ConfidenceLevel,
    ContributingRule,
    DevelopmentWorkflowGuide,
    DevelopmentWorkflowWorkerInput,
    DevelopmentWorkflowWorkerResult,
    EvidenceItem,
    FileNode,
    PullRequestWorkflow,
    QualityCommand,
    RuleType,
    SourceType,
    WorkerOutput,
    WorkerStatus,
)
from app.services.evidence_service import EvidenceService
from app.services.parser_service import ParserService
from app.workers.base_worker import BaseWorker


WORKFLOW_FILES = {
    "readme.md",
    "contributing.md",
    "code_of_conduct.md",
    "security.md",
    "package.json",
    "pyproject.toml",
    "setup.cfg",
    "tox.ini",
    "pytest.ini",
    "makefile",
    "dockerfile",
    "docker-compose.yml",
    ".prettierrc",
    ".eslintrc",
    "eslint.config.js",
    "eslint.config.mjs",
    "eslint.config.cjs",
    "ruff.toml",
    ".flake8",
    "mypy.ini",
    ".pre-commit-config.yaml",
}

COMMAND_RE = re.compile(
    r"^\s{0,4}(?:\$ )?((?:python|pip|uv|poetry|pdm|npm|pnpm|yarn|pytest|tox|ruff|black|flake8|mypy|pyright|eslint|prettier|tsc|make|docker|docker-compose|uvicorn)\s+[^\n`;&|]+)",
    re.MULTILINE,
)


class DevelopmentWorkflowWorker(BaseWorker[DevelopmentWorkflowWorkerInput, DevelopmentWorkflowWorkerResult]):
    worker_name = "Development Workflow Worker"

    def __init__(self) -> None:
        self.parser = ParserService()
        self.evidence_service = EvidenceService()

    def run(self, worker_input: DevelopmentWorkflowWorkerInput) -> DevelopmentWorkflowWorkerResult:
        root = Path(worker_input.repo_snapshot.local_path)
        files = worker_input.graph.files
        target_files = self._target_files(files)
        evidence: list[EvidenceItem] = []
        chunks: list[ChunkDoc] = []

        commands: list[QualityCommand] = []
        rules: list[ContributingRule] = []
        pr_workflows: list[PullRequestWorkflow] = []
        ci_rules: list[CIRule] = []
        uncertainties: list[str] = []

        for file_node in target_files:
            path = root / file_node.path
            text = self.parser.read_text(path)
            if not text:
                continue
            file_evidence = self._evidence(
                self._source_type(file_node.path),
                file_node.path,
                self._preview(text),
                "development workflow source discovered",
                file_node.path,
                1,
                min(file_node.line_count or 1, 80),
            )
            evidence.append(file_evidence)
            chunks.append(self._chunk(file_node.path, text, file_evidence.source_type, {"workflow_file": True}))

            commands.extend(self._commands_from_text(file_node.path, text, file_evidence.confidence))
            rules.extend(self._rules_from_text(file_node.path, text))
            if self._is_pr_template(file_node.path):
                pr_workflows.append(self._pr_workflow(file_node.path, text))
            if self._is_ci_file(file_node.path):
                ci_rule = self._ci_rule(file_node.path, text)
                ci_rules.append(ci_rule)
                commands.extend(ci_rule.commands)

        commands.extend(self._commands_from_package_json(root / "package.json"))
        commands.extend(self._commands_from_pyproject(root / "pyproject.toml"))
        commands.extend(self._commands_from_makefile(root / "Makefile"))
        commands.extend(self._commands_from_graph(worker_input.graph))
        commands = self._dedupe_commands(commands)

        contributing_files = {item.path.lower() for item in target_files}
        if "contributing.md" not in {Path(item).name for item in contributing_files}:
            uncertainties.append("仓库中未找到明确 CONTRIBUTING.md，贡献流程只能从 README、PR 模板或 CI 推断。")
        if not [command for command in commands if command.command_type == CommandType.LINT]:
            uncertainties.append("仓库中未找到明确 lint 命令或 lint 脚本。")
        if not [command for command in commands if command.command_type == CommandType.FORMAT]:
            uncertainties.append("仓库中未找到明确 format 命令或 format 脚本。")
        if not pr_workflows:
            uncertainties.append("仓库中未找到明确 PR 模板或 PR checklist。")
        if not ci_rules:
            uncertainties.append("仓库中未找到 GitHub Actions workflow，无法确认 CI 检查。")

        setup_steps = self._setup_steps(commands, target_files)
        guide = DevelopmentWorkflowGuide(
            repo_id=worker_input.repo_snapshot.repo_id,
            quality_commands=commands,
            setup_steps=setup_steps,
            development_commands=self._commands_of(commands, CommandType.SETUP, CommandType.DEV),
            test_commands=self._commands_of(commands, CommandType.TEST),
            lint_commands=self._commands_of(commands, CommandType.LINT),
            format_commands=self._commands_of(commands, CommandType.FORMAT),
            type_check_commands=self._commands_of(commands, CommandType.TYPE_CHECK),
            build_commands=self._commands_of(commands, CommandType.BUILD),
            branch_rules=[rule for rule in rules if rule.rule_type == RuleType.BRANCH],
            commit_rules=[rule for rule in rules if rule.rule_type == RuleType.COMMIT],
            contribution_rules=[rule for rule in rules if rule.rule_type == RuleType.CONTRIBUTION],
            pull_request_rules=pr_workflows,
            ci_rules=ci_rules,
            code_style_rules=[rule for rule in rules if rule.rule_type in {RuleType.STYLE, RuleType.CODE_STYLE}],
            setup_rules=[rule for rule in rules if rule.rule_type == RuleType.SETUP_RULE],
            test_rules=[rule for rule in rules if rule.rule_type == RuleType.TEST_RULE],
            documentation_references=[rule for rule in rules if rule.rule_type == RuleType.DOCUMENTATION_REFERENCE],
            project_safety_policies=[rule for rule in rules if rule.rule_type == RuleType.PROJECT_SAFETY_POLICY],
            contribution_steps=self._contribution_steps(rules, pr_workflows, commands),
            new_contributor_checklist=self._checklist(commands, rules, pr_workflows, ci_rules),
            evidence=evidence,
            uncertainties=uncertainties,
        )
        chunks.extend(self._guide_chunks(guide))

        output = WorkerOutput(
            worker_name=self.worker_name,
            task="extract development workflow, contribution rules, quality commands, PR rules and CI checks",
            status=WorkerStatus.SUCCESS if evidence or commands else WorkerStatus.PARTIAL,
            findings=[
                f"found {len(target_files)} workflow-related files",
                f"extracted {len(commands)} quality commands",
                f"extracted {len([rule for rule in rules if rule.rule_type in {RuleType.CONTRIBUTION, RuleType.BRANCH, RuleType.COMMIT, RuleType.STYLE, RuleType.CODE_STYLE}])} contribution/code-style rules",
                f"classified {len([rule for rule in rules if rule.rule_type == RuleType.PROJECT_SAFETY_POLICY])} project safety policy lines",
                f"classified {len([rule for rule in rules if rule.rule_type == RuleType.DOCUMENTATION_REFERENCE])} documentation references",
                f"found {len(ci_rules)} CI workflow files",
            ],
            evidence=evidence[:12],
            uncertainties=uncertainties,
            next_actions=["surface workflow guide in Development Workflow Panel", "use guide for contribution-related QA"],
        )
        return DevelopmentWorkflowWorkerResult(guide=guide, chunks=chunks, worker_output=output)

    def _target_files(self, files: list[FileNode]) -> list[FileNode]:
        targets: list[FileNode] = []
        for item in files:
            lowered = item.path.lower()
            name = Path(lowered).name
            if not self.parser.is_text_file(Path(item.path)) and not lowered.startswith(".github/workflows/"):
                continue
            if (
                name in WORKFLOW_FILES
                or self._is_relevant_docs_file(lowered)
                or lowered.startswith(".github/workflows/")
                or lowered.startswith(".github/pull_request_template")
                or "/pull_request_template" in lowered
                or "commitlint" in lowered
                or "husky" in lowered
                or "pre-commit" in lowered
            ):
                targets.append(item)
        return targets

    def _is_relevant_docs_file(self, lowered_path: str) -> bool:
        if not lowered_path.startswith(("docs/", "doc/")):
            return False
        relevant_terms = {
            "contributing",
            "contribute",
            "install",
            "installation",
            "setup",
            "development",
            "develop",
            "testing",
            "tests",
            "quickstart",
            "deploy",
            "requirements",
        }
        return any(term in lowered_path for term in relevant_terms)

    def _commands_from_text(self, source_file: str, text: str, confidence: float = 0.7) -> list[QualityCommand]:
        commands: list[QualityCommand] = []
        for line, command in self._command_lines(text):
            commands.append(
                QualityCommand(
                    name=self._command_name(command),
                    command=command,
                    command_type=self._classify_command(command),
                    source_file=source_file,
                    line_start=line,
                    line_end=line,
                    confidence=ConfidenceLevel.MEDIUM if confidence < 0.9 else ConfidenceLevel.HIGH,
                )
            )
        return commands

    def _command_lines(self, text: str) -> list[tuple[int, str]]:
        candidates: list[tuple[int, str]] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = COMMAND_RE.match(line)
            if not match:
                continue
            command = self._clean_command(match.group(1))
            if command:
                candidates.append((line_number, command))
        return candidates

    def _clean_command(self, command: str) -> str:
        command = command.strip().removeprefix("$").strip()
        if not command or command.startswith("#"):
            return ""
        if "\n" in command:
            command = command.splitlines()[0].strip()
        if command.startswith("make "):
            parts = command.split()
            if len(parts) > 1 and parts[1] in {"sure", "changes"}:
                return ""
        return command

    def _commands_from_package_json(self, path: Path) -> list[QualityCommand]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        scripts = data.get("scripts", {})
        commands: list[QualityCommand] = []
        if isinstance(scripts, dict):
            for script_name, script_body in scripts.items():
                command = f"npm run {script_name}" if script_name not in {"start", "test"} else f"npm {script_name}"
                commands.append(
                    QualityCommand(
                        name=f"package script: {script_name}",
                        command=command,
                        command_type=self._classify_command(f"{script_name} {script_body}"),
                        source_file="package.json",
                        confidence=ConfidenceLevel.HIGH,
                    )
                )
        if (path.parent / "package.json").exists():
            commands.append(
                QualityCommand(
                    name="install dependencies",
                    command="npm install",
                    command_type=CommandType.SETUP,
                    source_file="package.json",
                    confidence=ConfidenceLevel.HIGH,
                )
            )
        return commands

    def _commands_from_pyproject(self, path: Path) -> list[QualityCommand]:
        if not path.exists():
            return []
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return []
        commands: list[QualityCommand] = [
            QualityCommand(
                name="install dependencies",
                command="pip install -e .",
                command_type=CommandType.SETUP,
                source_file="pyproject.toml",
                confidence=ConfidenceLevel.MEDIUM,
            )
        ]
        tool = data.get("tool", {})
        if "pytest" in tool:
            commands.append(self._quality_command("pytest", "pytest", CommandType.TEST, "pyproject.toml"))
        if "ruff" in tool:
            commands.append(self._quality_command("ruff check", "ruff check .", CommandType.LINT, "pyproject.toml"))
        if "black" in tool:
            commands.append(self._quality_command("black format", "black .", CommandType.FORMAT, "pyproject.toml"))
        if "mypy" in tool:
            commands.append(self._quality_command("mypy", "mypy .", CommandType.TYPE_CHECK, "pyproject.toml"))
        scripts = data.get("project", {}).get("scripts", {})
        for script_name in scripts:
            commands.append(self._quality_command(f"project script: {script_name}", f"python -m {script_name}", CommandType.DEV, "pyproject.toml"))
        return commands

    def _commands_from_makefile(self, path: Path) -> list[QualityCommand]:
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8", errors="ignore")
        commands: list[QualityCommand] = []
        for match in re.finditer(r"^([A-Za-z0-9_\-]+):", text, flags=re.MULTILINE):
            target = match.group(1)
            line = text[: match.start()].count("\n") + 1
            commands.append(
                QualityCommand(
                    name=f"make {target}",
                    command=f"make {target}",
                    command_type=self._classify_command(target),
                    source_file="Makefile",
                    line_start=line,
                    line_end=line,
                    confidence=ConfidenceLevel.HIGH,
                )
            )
        return commands

    def _commands_from_graph(self, graph) -> list[QualityCommand]:
        commands: list[QualityCommand] = []
        for command in graph.run_commands:
            commands.append(
                QualityCommand(
                    name="graph run command",
                    command=command,
                    command_type=self._classify_command(command),
                    source_file="RepositoryIntelligenceGraph",
                    confidence=ConfidenceLevel.LOW,
                )
            )
        for command in graph.test_commands:
            commands.append(
                QualityCommand(
                    name="graph test command",
                    command=command,
                    command_type=CommandType.TEST,
                    source_file="RepositoryIntelligenceGraph",
                    confidence=ConfidenceLevel.LOW,
                )
            )
        for command in graph.build_commands:
            commands.append(
                QualityCommand(
                    name="graph build command",
                    command=command,
                    command_type=CommandType.BUILD,
                    source_file="RepositoryIntelligenceGraph",
                    confidence=ConfidenceLevel.LOW,
                )
            )
        return commands

    def _rules_from_text(self, source_file: str, text: str) -> list[ContributingRule]:
        rules: list[ContributingRule] = []
        for line, raw_line in enumerate(text.splitlines(), start=1):
            description = raw_line.strip()
            if len(description) < 8:
                continue
            rule_type = self._rule_type_for_line(source_file, description)
            if not rule_type:
                continue
            evidence = [
                self._evidence(
                    self._rule_source_type(rule_type, source_file),
                    source_file,
                    description,
                    f"{rule_type.value} extracted from workflow source",
                    source_file,
                    line,
                    line,
                    0.8,
                )
            ]
            rules.append(
                ContributingRule(
                    rule_type=rule_type,
                    description=description[:500],
                    source_file=source_file,
                    evidence=evidence,
                    confidence=ConfidenceLevel.HIGH if "contributing" in source_file.lower() else ConfidenceLevel.MEDIUM,
                )
            )
        return self._dedupe_rules(rules)

    def _ci_rule(self, source_file: str, text: str) -> CIRule:
        workflow_name = self._first_group(r"(?m)^name:\s*(.+)$", text)
        triggers = self._extract_triggers(text)
        jobs = re.findall(r"(?m)^\s{2}([A-Za-z0-9_\-]+):\s*$", text)
        commands: list[QualityCommand] = []
        for match in re.finditer(r"(?m)^\s*run:\s*(.+)$", text):
            command = match.group(1).strip()
            line = text[: match.start()].count("\n") + 1
            commands.append(
                QualityCommand(
                    name=f"CI: {self._command_name(command)}",
                    command=command,
                    command_type=CommandType.CI if self._classify_command(command) == CommandType.UNKNOWN else self._classify_command(command),
                    source_file=source_file,
                    line_start=line,
                    line_end=line,
                    confidence=ConfidenceLevel.HIGH,
                )
            )
        evidence = [
            self._evidence(
                SourceType.CI,
                source_file,
                self._preview(text),
                "GitHub Actions workflow discovered",
                source_file,
                1,
                min(text.count("\n") + 1, 80),
                0.95,
            )
        ]
        commands = self._dedupe_commands(commands)
        return CIRule(
            workflow_file=source_file,
            workflow_name=workflow_name,
            triggers=triggers,
            jobs=jobs,
            commands=commands,
            required_for_pr=True if "pull_request" in triggers else None,
            evidence=evidence,
        )

    def _pr_workflow(self, source_file: str, text: str) -> PullRequestWorkflow:
        checklist = [line.strip("- []\t ") for line in text.splitlines() if re.match(r"^\s*[-*]\s*\[[ xX]?\]", line)]
        steps = [line.strip("#*-\t ") for line in text.splitlines() if re.search(r"(?i)\b(test|issue|screenshot|benchmark|description|checklist|review)\b", line)]
        evidence = [
            self._evidence(
                SourceType.PR_TEMPLATE,
                source_file,
                self._preview(text),
                "PR template discovered",
                source_file,
                1,
                min(text.count("\n") + 1, 80),
                0.95,
            )
        ]
        return PullRequestWorkflow(
            steps=steps[:10],
            checklist=checklist[:20],
            required_checks=[],
            source_file=source_file,
            evidence=evidence,
            uncertainties=[] if checklist or steps else ["PR template exists but no checklist items were detected"],
        )

    def _guide_chunks(self, guide: DevelopmentWorkflowGuide) -> list[ChunkDoc]:
        chunks: list[ChunkDoc] = []
        for command in guide.development_commands + guide.test_commands + guide.lint_commands + guide.format_commands + guide.type_check_commands + guide.build_commands:
            chunks.append(
                ChunkDoc(
                    chunk_id=str(uuid5(NAMESPACE_URL, f"workflow-command:{guide.repo_id}:{command.command}:{command.source_file}")),
                    source_type=SourceType.WORKFLOW,
                    file_path=command.source_file,
                    title=command.name,
                    text=command.command,
                    line_start=command.line_start or 1,
                    line_end=command.line_end or command.line_start or 1,
                    metadata={"command_type": command.command_type.value, "confidence": command.confidence.value},
                )
            )
        for rule in (
            guide.branch_rules
            + guide.commit_rules
            + guide.contribution_rules
            + guide.code_style_rules
            + guide.setup_rules
            + guide.test_rules
            + guide.documentation_references
            + guide.project_safety_policies
        ):
            chunks.append(
                ChunkDoc(
                    chunk_id=str(uuid5(NAMESPACE_URL, f"workflow-rule:{guide.repo_id}:{rule.rule_type}:{rule.description[:80]}")),
                    source_type=SourceType.CONTRIBUTING,
                    file_path=rule.source_file,
                    title=f"{rule.rule_type.value} rule",
                    text=rule.description,
                    metadata={"rule_type": rule.rule_type.value, "confidence": rule.confidence.value},
                )
            )
        for ci_rule in guide.ci_rules:
            chunks.append(
                ChunkDoc(
                    chunk_id=str(uuid5(NAMESPACE_URL, f"ci:{guide.repo_id}:{ci_rule.workflow_file}")),
                    source_type=SourceType.CI,
                    file_path=ci_rule.workflow_file,
                    title=ci_rule.workflow_name or ci_rule.workflow_file,
                    text="; ".join(command.command for command in ci_rule.commands) or ci_rule.workflow_file,
                    metadata={"source_type": "ci"},
                )
            )
        return chunks

    def _chunk(self, file_path: str, text: str, source_type: SourceType, metadata: dict[str, object]) -> ChunkDoc:
        return ChunkDoc(
            chunk_id=str(uuid5(NAMESPACE_URL, f"workflow-source:{file_path}")),
            source_type=source_type,
            file_path=file_path,
            title=file_path,
            text=text[:1800],
            line_start=1,
            line_end=min(text.count("\n") + 1, 80),
            metadata=metadata,
        )

    def _setup_steps(self, commands: list[QualityCommand], target_files: list[FileNode]) -> list[str]:
        steps = []
        if any(Path(item.path).name.lower() == "readme.md" for item in target_files):
            steps.append("先阅读 README，确认项目安装、启动和测试入口。")
        if any(Path(item.path).name.lower() == "contributing.md" for item in target_files):
            steps.append("阅读 CONTRIBUTING，确认贡献流程和维护者要求。")
        for command in self._commands_of(commands, CommandType.SETUP)[:4]:
            steps.append(f"安装依赖：{command.command}")
        for command in self._commands_of(commands, CommandType.DEV)[:4]:
            steps.append(f"启动开发环境：{command.command}")
        if any(Path(item.path).name.lower() in {"dockerfile", "docker-compose.yml"} for item in target_files):
            steps.append("仓库包含 Docker 配置，按文档确认是否需要容器环境。")
        return steps

    def _contribution_steps(self, rules: list[ContributingRule], pr_workflows: list[PullRequestWorkflow], commands: list[QualityCommand]) -> list[str]:
        steps = ["确认 README/CONTRIBUTING 中的贡献入口。"]
        if any(rule.rule_type == RuleType.CONTRIBUTION and "issue" in rule.description.lower() for rule in rules):
            steps.append("先查看或关联对应 issue。")
        if any(rule.rule_type == RuleType.BRANCH for rule in rules):
            steps.append("按仓库证据中的分支规范创建工作分支。")
        if commands:
            steps.append("修改前后运行仓库证据中的测试、lint、format 或构建命令。")
        if pr_workflows:
            steps.append("按 PR 模板填写 checklist、测试结果和关联 issue。")
        return steps

    def _checklist(self, commands: list[QualityCommand], rules: list[ContributingRule], pr_workflows: list[PullRequestWorkflow], ci_rules: list[CIRule]) -> list[str]:
        checklist = ["阅读 README 和可用贡献文档。"]
        if self._commands_of(commands, CommandType.SETUP):
            checklist.append("按证据中的安装命令准备本地环境。")
        if self._commands_of(commands, CommandType.TEST):
            checklist.append("运行测试命令并记录结果。")
        if self._commands_of(commands, CommandType.LINT):
            checklist.append("运行 lint 命令。")
        if self._commands_of(commands, CommandType.FORMAT):
            checklist.append("运行 format 命令。")
        if self._commands_of(commands, CommandType.TYPE_CHECK):
            checklist.append("运行类型检查命令。")
        if any(rule.rule_type in {RuleType.BRANCH, RuleType.COMMIT, RuleType.CONTRIBUTION} for rule in rules):
            checklist.append("遵守分支或提交信息规范。")
        if pr_workflows:
            checklist.append("按 PR 模板填写说明、checklist 和验证信息。")
        if ci_rules:
            checklist.append("确认 GitHub Actions/CI 中的检查项本地可复现或已说明。")
        return checklist

    def _source_type(self, file_path: str) -> SourceType:
        lowered = file_path.lower()
        if self._is_ci_file(lowered):
            return SourceType.CI
        if self._is_pr_template(lowered):
            return SourceType.PR_TEMPLATE
        if "contributing" in lowered or "code_of_conduct" in lowered or "security" in lowered:
            return SourceType.CONTRIBUTING
        if any(name in lowered for name in ["prettier", "eslint", "ruff", "flake8", "mypy", "pre-commit"]):
            return SourceType.STYLE
        return SourceType.WORKFLOW

    def _is_ci_file(self, file_path: str) -> bool:
        lowered = file_path.lower()
        return lowered.startswith(".github/workflows/") and lowered.endswith((".yml", ".yaml"))

    def _is_pr_template(self, file_path: str) -> bool:
        return "pull_request_template" in file_path.lower()

    def _extract_triggers(self, text: str) -> list[str]:
        triggers: set[str] = set()
        for trigger in ["push", "pull_request", "workflow_dispatch", "schedule", "release"]:
            if re.search(rf"(?m)^\s*{trigger}\s*:", text) or trigger in text:
                triggers.add(trigger)
        return sorted(triggers)

    def _classify_command(self, command: str) -> CommandType:
        text = command.lower()
        if any(token in text for token in ["install", "sync", "setup", "bootstrap"]):
            return CommandType.SETUP
        if any(token in text for token in ["dev", "start", "serve", "uvicorn"]):
            return CommandType.DEV
        if any(token in text for token in ["test", "pytest", "jest", "vitest", "coverage", "tox"]):
            return CommandType.TEST
        if any(token in text for token in ["lint", "ruff check", "flake8", "eslint"]):
            return CommandType.LINT
        if any(token in text for token in ["format", "black", "prettier", "ruff format"]):
            return CommandType.FORMAT
        if any(token in text for token in ["mypy", "pyright", "tsc", "typecheck", "type-check"]):
            return CommandType.TYPE_CHECK
        if "build" in text:
            return CommandType.BUILD
        return CommandType.UNKNOWN

    def _quality_command(self, name: str, command: str, command_type: CommandType, source_file: str) -> QualityCommand:
        return QualityCommand(name=name, command=command, command_type=command_type, source_file=source_file, confidence=ConfidenceLevel.HIGH)

    def _commands_of(self, commands: list[QualityCommand], *command_types: CommandType) -> list[QualityCommand]:
        allowed = set(command_types)
        return [command for command in commands if command.command_type in allowed]

    def _dedupe_commands(self, commands: list[QualityCommand]) -> list[QualityCommand]:
        seen: dict[tuple[str, str], QualityCommand] = {}
        confidence_rank = {"low": 1, "medium": 2, "high": 3}
        for command in commands:
            normalized = self._normalize_command(command.command)
            if not normalized:
                continue
            source_file = command.source_file.replace("\\", "/")
            command.command = normalized
            command.source_file = source_file
            sources = set(command.evidence_sources or [])
            sources.add(source_file)
            command.evidence_sources = sorted(source.replace("\\", "/") for source in sources if source)
            key = (command.command_type.value, normalized)
            existing = seen.get(key)
            if existing is None:
                seen[key] = command
                continue
            merged_sources = sorted(set(existing.evidence_sources + command.evidence_sources))
            existing.evidence_sources = merged_sources
            if confidence_rank.get(command.confidence.value, 0) > confidence_rank.get(existing.confidence.value, 0):
                command.evidence_sources = merged_sources
                seen[key] = command
        return list(seen.values())

    def _dedupe_rules(self, rules: list[ContributingRule]) -> list[ContributingRule]:
        seen: dict[tuple[str, str, str], ContributingRule] = {}
        for rule in rules:
            seen[(rule.rule_type.value, rule.source_file, rule.description)] = rule
        return list(seen.values())

    def _rule_type_for_line(self, source_file: str, line: str) -> RuleType | None:
        text = line.lower()
        source = source_file.lower()
        if self._looks_like_project_safety_policy(text):
            return RuleType.PROJECT_SAFETY_POLICY
        if self._looks_like_documentation_reference(text):
            return RuleType.DOCUMENTATION_REFERENCE
        if re.search(r"\b(branch|feature/|bugfix/)\b|分支", text):
            return RuleType.BRANCH
        if re.search(r"\b(commit|conventional commits|commitlint|sign-off|squash)\b|提交", text):
            return RuleType.COMMIT
        if re.search(r"\b(contributing|contribution|contributor|maintainer|reviewer|review|pull request|pr checklist|good first|issue)\b|贡献|维护者|审核", text):
            if "pull_request_template" in source:
                return RuleType.PR
            return RuleType.CONTRIBUTION
        if re.search(r"\b(lint|format|ruff|black|prettier|eslint|flake8|mypy|pyright|type check|style guide)\b|代码规范|格式", text):
            return RuleType.CODE_STYLE
        if re.search(r"\b(pytest|test command|unit test|coverage|test suite)\b|测试", text):
            return RuleType.TEST_RULE
        if re.search(r"\b(install|setup|quick start|quickstart|requirements|run_demo|start|启动)\b|安装|启动", text):
            return RuleType.SETUP_RULE
        if re.search(r"\b(ci|github actions|workflow)\b", text):
            return RuleType.CI
        return None

    def _looks_like_project_safety_policy(self, text: str) -> bool:
        return bool(
            re.search(
                r"\b(safety|safe|risk|hazard|policy|contract|constraint|guardrail|medical|emergency|oxygen|power outage|resilience|harm|refuse)\b|安全|风险|约束|策略",
                text,
            )
        )

    def _looks_like_documentation_reference(self, text: str) -> bool:
        return bool(
            re.search(r"\b(docs/|documentation|readme|reference|report|architecture|checklist|\.md)\b|文档|参考|报告|架构", text)
        )

    def _rule_source_type(self, rule_type: RuleType, source_file: str) -> SourceType:
        if rule_type == RuleType.CI:
            return SourceType.CI
        if rule_type == RuleType.CODE_STYLE:
            return SourceType.STYLE
        if rule_type in {RuleType.CONTRIBUTION, RuleType.BRANCH, RuleType.COMMIT, RuleType.PR}:
            return SourceType.CONTRIBUTING if "contributing" in source_file.lower() else SourceType.WORKFLOW
        return SourceType.WORKFLOW

    def _command_name(self, command: str) -> str:
        return command.split()[0] if command.split() else "command"

    def _normalize_command(self, command: str) -> str:
        return " ".join(command.replace("\\", "/").strip().split())

    def _first_group(self, pattern: str, text: str) -> str | None:
        match = re.search(pattern, text)
        return match.group(1).strip() if match else None

    def _preview(self, text: str) -> str:
        return "\n".join(line for line in text.splitlines()[:30] if line.strip())[:900]

    def _evidence(
        self,
        source_type: SourceType,
        source_ref: str,
        quote: str,
        supports_claim: str,
        file_path: str,
        line_start: int | None = None,
        line_end: int | None = None,
        confidence: float = 0.85,
    ) -> EvidenceItem:
        return self.evidence_service.make(
            source_type,
            source_ref,
            quote,
            supports_claim,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            confidence=confidence,
        )

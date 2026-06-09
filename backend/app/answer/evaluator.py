from __future__ import annotations

import re

from app.core.schemas import AnswerBundle, RepositoryIntelligenceGraph, SelfCheckReport, SourceType, SuggestedAction, TaskType


class Evaluator:
    def evaluate(self, bundle: AnswerBundle, graph: RepositoryIntelligenceGraph) -> SelfCheckReport:
        missing: list[str] = []
        risks: list[str] = []
        conflicts: list[str] = []
        missing_file_uncertainty: list[str] = []
        missing_command_uncertainty: list[str] = []
        hallucinated_file: list[str] = []
        hallucinated_command: list[str] = []
        hallucinated_issue: list[str] = []
        answer_text = "\n".join([bundle.conclusion, *bundle.steps, *bundle.risks, *bundle.uncertainties])

        evidence_types = {item.source_type for item in bundle.evidence}
        has_docs_or_graph = bool(evidence_types & {SourceType.DOCS, SourceType.GRAPH})
        has_code_or_graph = bool(evidence_types & {SourceType.CODE, SourceType.TEST, SourceType.TESTS, SourceType.CONFIG, SourceType.BUILD, SourceType.GRAPH})
        has_issue_or_internal = bool(evidence_types & {SourceType.ISSUE, SourceType.ISSUES, SourceType.INTERNAL_SUGGESTION})
        has_workflow_evidence = bool(evidence_types & {SourceType.WORKFLOW, SourceType.CONTRIBUTING, SourceType.CI, SourceType.STYLE, SourceType.PR_TEMPLATE, SourceType.COMMAND})
        has_config_or_code_evidence = bool(evidence_types & {SourceType.CONFIG, SourceType.CODE, SourceType.BUILD, SourceType.GRAPH, SourceType.COMMAND})
        has_build_or_config_evidence = bool(evidence_types & {SourceType.BUILD, SourceType.CONFIG, SourceType.COMMAND, SourceType.GRAPH})
        answer_type = bundle.answer_type or (bundle.task_type.value if bundle.task_type else "")

        if not bundle.evidence:
            missing.append("answer has no EvidenceItem")
            if bundle.confidence > 0.45:
                risks.append("evidence is empty but answer confidence is not low")
        if bundle.conclusion and not bundle.evidence and "证据不足" not in bundle.conclusion:
            missing.append("conclusion is not evidence-backed")
        if "配置文件" in bundle.conclusion and not has_config_or_code_evidence:
            missing.append("conclusion mentions 配置文件 but has no config/code evidence")
        if "构建脚本" in bundle.conclusion and not has_build_or_config_evidence:
            missing.append("conclusion mentions 构建脚本 but has no build/config evidence")
        if not has_config_or_code_evidence and any(term in bundle.conclusion for term in ["配置文件", "构建脚本"]):
            missing.append("evidence_code is empty; do not claim config/build directly supports the conclusion")
        if answer_type in {"overview", "docs_recommendation", "learning_path"} or bundle.task_type in {TaskType.REPO_OVERVIEW, TaskType.LEARNING_PATH}:
            if not has_docs_or_graph:
                missing.append(f"{answer_type or bundle.task_type} requires docs or graph evidence")
        if answer_type in {"entrypoints", "core_modules"}:
            if not has_code_or_graph:
                missing.append(f"{answer_type} requires code or graph evidence")
        if answer_type == "beginner_tasks":
            if not has_issue_or_internal:
                missing.append("beginner_tasks requires issue evidence or internal task evidence")
        if answer_type == "development_workflow" or bundle.task_type == TaskType.DEVELOPMENT_WORKFLOW:
            if not has_workflow_evidence:
                missing.append("development_workflow requires Development Workflow Worker or command evidence")

        command_evidence = {
            (command.command_type.value, self._normalize_command(command.command)): command
            for command in graph.quality_commands
        }
        known_commands = {
            self._normalize_command(command)
            for command in graph.run_commands
            + graph.test_commands
            + graph.build_commands
            + graph.setup_commands
            + graph.lint_commands
            + graph.format_commands
            + graph.type_check_commands
        }
        known_commands.update(key[1] for key in command_evidence)
        for ci_rule in graph.ci_rules:
            for command in ci_rule.commands:
                normalized = self._normalize_command(command.command)
                known_commands.add(normalized)
                command_evidence[(command.command_type.value, normalized)] = command
        for entrypoint in graph.entrypoints:
            for command in self._mentioned_commands(f"{entrypoint.source} {entrypoint.reason}"):
                known_commands.add(self._normalize_command(command))

        known_files = {item.path.replace("\\", "/") for item in graph.files}
        known_symbols = {item.name for item in graph.symbols}
        evidence_issue_numbers = {item.issue_number for item in bundle.evidence if item.issue_number is not None}

        for file_path in self._mentioned_files(answer_text):
            if not self._file_is_known(file_path, known_files):
                if self._is_missing_file_statement(file_path, answer_text):
                    missing_file_uncertainty.append(file_path)
                else:
                    hallucinated_file.append(file_path)
                    risks.append(f"model output mentions file without graph evidence: {file_path}")
        for command in self._mentioned_commands(answer_text):
            normalized = self._normalize_command(command)
            if not self._command_is_known(normalized, known_commands):
                if self._is_missing_command_statement(command, answer_text):
                    missing_command_uncertainty.append(command)
                else:
                    hallucinated_command.append(command)
                    risks.append(f"model output mentions command without graph evidence: {command}")
        for keyword in ["lint", "format", "type check", "类型检查"]:
            if self._is_missing_keyword_statement(keyword, answer_text) and not any(keyword.lower() in command.lower() for command in known_commands):
                missing_command_uncertainty.append(keyword)
        for issue_number in self._mentioned_issue_numbers(answer_text):
            if issue_number not in evidence_issue_numbers:
                hallucinated_issue.append(f"#{issue_number}")
                risks.append(f"model output mentions issue without Issue Worker evidence: #{issue_number}")
        for symbol_name in self._mentioned_symbols(answer_text):
            if known_symbols and symbol_name not in known_symbols:
                risks.append(f"model output mentions symbol without Symbol Graph evidence: {symbol_name}")

        for command in bundle.verifiable_commands:
            normalized = self._normalize_command(command)
            if not self._command_is_known(normalized, known_commands) and not command.startswith("推测:"):
                missing.append(f"verifiable command has no graph evidence: {command}")
                continue
            matched = [item for (_, item_command), item in command_evidence.items() if item_command == normalized]
            if not matched or not any(item.evidence_sources or item.source_file for item in matched):
                missing.append(f"verifiable command has no evidence source: {command}")

        if graph.development_workflow and "开发流程" in bundle.conclusion:
            guide = graph.development_workflow
            if not guide.evidence:
                missing.append("Development Workflow Guide has no evidence")
            if not guide.pull_request_rules and any("PR" in step or "pull request" in step.lower() for step in bundle.steps):
                risks.append("PR workflow is mentioned but no PR template evidence was found")
            if not guide.branch_rules and any("分支" in step or "branch" in step.lower() for step in bundle.steps):
                risks.append("branch rules are mentioned but no branch-rule evidence was found")
            if not guide.commit_rules and any("commit" in step.lower() or "提交" in step for step in bundle.steps):
                risks.append("commit rules are mentioned but no commit-rule evidence was found")
            if not guide.lint_commands and any("lint" in step.lower() for step in bundle.steps):
                if any(self._is_missing_keyword_statement("lint", step) for step in bundle.steps):
                    missing_command_uncertainty.append("lint")
                else:
                    risks.append("lint is mentioned but no lint command evidence was found")
            if not guide.format_commands and any("format" in step.lower() for step in bundle.steps):
                if any(self._is_missing_keyword_statement("format", step) for step in bundle.steps):
                    missing_command_uncertainty.append("format")
                else:
                    risks.append("format is mentioned but no format command evidence was found")
            risks.extend(self._command_conflicts(graph))

        evidence_coverage = min(1.0, len(bundle.evidence) / max(1, len(bundle.steps) + 1))
        passed = not missing and not risks and not conflicts
        if "证据不足" in bundle.conclusion:
            passed = False

        action = SuggestedAction.ACCEPT
        if missing:
            action = SuggestedAction.RETRIEVE_MORE
        if risks:
            action = SuggestedAction.LOWER_CONFIDENCE
        if conflicts:
            action = SuggestedAction.REVISE

        return SelfCheckReport(
            passed=passed,
            evidence_coverage=evidence_coverage,
            hallucination_risks=risks,
            missing_evidence=missing,
            missing_file_uncertainty=self._dedupe_strings(missing_file_uncertainty),
            missing_command_uncertainty=self._dedupe_strings(missing_command_uncertainty),
            hallucinated_file=self._dedupe_strings(hallucinated_file),
            hallucinated_command=self._dedupe_strings(hallucinated_command),
            hallucinated_issue=self._dedupe_strings(hallucinated_issue),
            conflicts=conflicts,
            suggested_action=action,
        )

    def _command_conflicts(self, graph: RepositoryIntelligenceGraph) -> list[str]:
        conflicts: list[str] = []
        if not graph.development_workflow:
            return conflicts
        ci_commands = {command.command for rule in graph.ci_rules for command in rule.commands}
        local_commands = {command.command for command in graph.quality_commands if command.command_type.value != "ci"}
        if ci_commands and local_commands:
            ci_test_like = {command for command in ci_commands if "test" in command.lower() or "pytest" in command.lower()}
            local_test_like = {command for command in local_commands if "test" in command.lower() or "pytest" in command.lower()}
            if ci_test_like and local_test_like and ci_test_like.isdisjoint(local_test_like):
                conflicts.append("CI test commands differ from local documented test commands")
        return conflicts

    def _normalize_command(self, command: str) -> str:
        return " ".join(command.replace("\\", "/").strip().split())

    def _command_is_known(self, normalized: str, known_commands: set[str]) -> bool:
        return normalized in known_commands or any(
            known.startswith(normalized) or normalized.startswith(known)
            for known in known_commands
            if normalized and known
        )

    def _file_is_known(self, file_path: str, known_files: set[str]) -> bool:
        normalized = file_path.replace("\\", "/").removeprefix("./")
        return normalized in known_files or any(path.endswith(f"/{normalized}") for path in known_files)

    def _is_missing_file_statement(self, file_path: str, text: str) -> bool:
        normalized = text.replace("\\", "/")
        escaped = re.escape(file_path.replace("\\", "/"))
        return bool(
            re.search(rf"(未找到|没有找到|未检测到|缺少|不存在|no|not found)[^。；\n]{{0,80}}{escaped}", normalized, flags=re.IGNORECASE)
            or re.search(rf"{escaped}[^。；\n]{{0,80}}(未找到|没有找到|未检测到|缺少|不存在|not found)", normalized, flags=re.IGNORECASE)
        )

    def _is_missing_command_statement(self, command: str, text: str) -> bool:
        normalized = text.replace("\\", "/")
        command_norm = re.escape(self._normalize_command(command))
        return bool(
            re.search(rf"(未找到|没有找到|未检测到|暂无|缺少|no|not found)[^。；\n]{{0,80}}{command_norm}", normalized, flags=re.IGNORECASE)
            or re.search(rf"{command_norm}[^。；\n]{{0,80}}(未找到|没有找到|未检测到|暂无|缺少|not found)", normalized, flags=re.IGNORECASE)
        )

    def _is_missing_keyword_statement(self, keyword: str, text: str) -> bool:
        return bool(
            re.search(rf"(未找到|没有找到|未检测到|暂无|缺少|no|not found)[^。；\n]{{0,80}}{re.escape(keyword)}", text, flags=re.IGNORECASE)
            or re.search(rf"{re.escape(keyword)}[^。；\n]{{0,80}}(未找到|没有找到|未检测到|暂无|缺少|not found)", text, flags=re.IGNORECASE)
        )

    def _dedupe_strings(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    def _mentioned_files(self, text: str) -> list[str]:
        pattern = r"(?<![\w:/.-])(?:[\w.-]+/)*[\w.-]+\.(?:py|js|jsx|ts|tsx|md|json|jsonl|toml|yaml|yml|html|css|txt|bib|cfg|ini)(?![\w.-])"
        return sorted({item.replace("\\", "/") for item in re.findall(pattern, text)})

    def _mentioned_commands(self, text: str) -> list[str]:
        pattern = (
            r"(?:python(?:[ \t]+-m)?[ \t]+[\w./\\-]+(?:[ \t]+[\w./\\:=@\"'-]+){0,8}"
            r"|pip[ \t]+install[ \t]+[\w./\\:=@\"'-]+(?:[ \t]+[\w./\\:=@\"'-]+){0,8}"
            r"|pytest(?:[ \t]+[\w./\\:=@\"'-]+){0,6}"
            r"|npm[ \t]+\w+(?:[ \t]+[\w./\\:=@\"'-]+){0,6})"
        )
        commands = []
        for match in re.findall(pattern, text):
            command = match.strip().strip("。；;，,")
            if command:
                commands.append(command)
        return sorted(set(commands))

    def _mentioned_issue_numbers(self, text: str) -> list[int]:
        values = re.findall(r"(?:issue\s*#?|#)(\d+)", text, flags=re.IGNORECASE)
        return sorted({int(value) for value in values})

    def _mentioned_symbols(self, text: str) -> list[str]:
        ignored = {"print", "len", "str", "int", "list", "dict", "set", "open", "json"}
        values = re.findall(r"\b([A-Za-z_]\w*)\(\)", text)
        return sorted({value for value in values if value not in ignored})

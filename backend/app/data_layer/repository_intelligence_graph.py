from __future__ import annotations

from app.core.schemas import (
    CIRule,
    ContributingRule,
    DevelopmentWorkflowGuide,
    EdgeType,
    EntryPointCandidate,
    FileNode,
    GraphEdge,
    QualityCommand,
    RepositoryIntelligenceGraph,
    RuleType,
    SymbolNode,
)


class RepositoryIntelligenceGraphStore:
    def __init__(self, graph: RepositoryIntelligenceGraph | None = None) -> None:
        self.graph = graph or RepositoryIntelligenceGraph()

    def add_files(self, files: list[FileNode]) -> None:
        by_path = {item.path: item for item in self.graph.files}
        by_path.update({item.path: item for item in files})
        self.graph.files = list(by_path.values())
        self.graph.docs = [item for item in self.graph.files if item.file_type.value.startswith("docs")]
        self.graph.build_scripts = [item for item in self.graph.files if item.file_type.value == "build"]

    def add_symbols(self, symbols: list[SymbolNode]) -> None:
        keys = {(item.file_path, item.name, item.line_start): item for item in self.graph.symbols}
        keys.update({(item.file_path, item.name, item.line_start): item for item in symbols})
        self.graph.symbols = list(keys.values())

    def add_edges(self, edges: list[GraphEdge]) -> None:
        keys = {(edge.source, edge.target, edge.edge_type): edge for edge in self.graph.edges}
        keys.update({(edge.source, edge.target, edge.edge_type): edge for edge in edges})
        self.graph.edges = list(keys.values())
        self.graph.imports = [edge for edge in self.graph.edges if edge.edge_type == EdgeType.IMPORTS]
        self.graph.tests = [edge for edge in self.graph.edges if edge.edge_type == EdgeType.TESTS]

    def merge(self, graph: RepositoryIntelligenceGraph) -> None:
        self.add_files(graph.files)
        self.add_symbols(graph.symbols)
        self.add_edges(graph.edges + graph.imports + graph.tests)
        self.graph.key_files = sorted(set(self.graph.key_files + graph.key_files))
        self.graph.languages = self._merge_language_counts(self.graph.languages, graph.languages)
        self.graph.core_directories = self._merge_ordered(self.graph.core_directories, graph.core_directories)
        self.graph.entrypoints = self._merge_entrypoints(self.graph.entrypoints, graph.entrypoints)
        self.graph.setup_commands = self._merge_ordered(self.graph.setup_commands, graph.setup_commands)
        self.graph.run_commands = self._merge_ordered(self.graph.run_commands, graph.run_commands)
        self.graph.test_commands = self._merge_ordered(self.graph.test_commands, graph.test_commands)
        self.graph.build_commands = self._merge_ordered(self.graph.build_commands, graph.build_commands)
        self.graph.lint_commands = self._merge_ordered(self.graph.lint_commands, graph.lint_commands)
        self.graph.format_commands = self._merge_ordered(self.graph.format_commands, graph.format_commands)
        self.graph.type_check_commands = self._merge_ordered(self.graph.type_check_commands, graph.type_check_commands)
        if graph.development_workflow:
            self.set_development_workflow(graph.development_workflow)
        self.graph.quality_commands = self._dedupe_quality_commands(self.graph.quality_commands + graph.quality_commands)
        self.graph.contributing_rules = self._dedupe_contributing_rules(self.graph.contributing_rules + graph.contributing_rules)
        self.graph.ci_rules = self.graph.ci_rules + [
            rule for rule in graph.ci_rules if rule.workflow_file not in {item.workflow_file for item in self.graph.ci_rules}
        ]

    def set_development_workflow(self, guide: DevelopmentWorkflowGuide) -> None:
        self.graph.development_workflow = guide
        self.graph.quality_commands = self._dedupe_quality_commands(
            self.graph.quality_commands
            + guide.development_commands
            + guide.test_commands
            + guide.lint_commands
            + guide.format_commands
            + guide.type_check_commands
            + guide.build_commands
            + [command for ci_rule in guide.ci_rules for command in ci_rule.commands]
        )
        self.graph.contributing_rules = self._dedupe_contributing_rules(
            self.graph.contributing_rules
            + guide.branch_rules
            + guide.commit_rules
            + guide.contribution_rules
            + guide.code_style_rules
            + guide.setup_rules
            + guide.test_rules
            + guide.documentation_references
            + guide.project_safety_policies
        )
        self.graph.ci_rules = guide.ci_rules
        self.graph.setup_commands = self._merge_ordered(self.graph.setup_commands, [command.command for command in guide.development_commands if command.command_type.value == "setup"])
        self.graph.run_commands = self._merge_ordered(self.graph.run_commands, [command.command for command in guide.development_commands if command.command_type.value == "dev"])
        self.graph.test_commands = self._merge_ordered(self.graph.test_commands, [command.command for command in guide.test_commands])
        self.graph.build_commands = self._merge_ordered(self.graph.build_commands, [command.command for command in guide.build_commands])
        self.graph.lint_commands = self._merge_ordered(self.graph.lint_commands, [command.command for command in guide.lint_commands])
        self.graph.format_commands = self._merge_ordered(self.graph.format_commands, [command.command for command in guide.format_commands])
        self.graph.type_check_commands = self._merge_ordered(self.graph.type_check_commands, [command.command for command in guide.type_check_commands])

    def get_file(self, path: str) -> FileNode | None:
        return next((item for item in self.graph.files if item.path == path), None)

    def find_symbol(self, name: str) -> list[SymbolNode]:
        needle = name.lower()
        return [item for item in self.graph.symbols if needle in item.name.lower()]

    def get_imports(self, file_path: str) -> list[GraphEdge]:
        return [edge for edge in self.graph.imports if edge.source == file_path]

    def get_imported_by(self, file_path: str) -> list[GraphEdge]:
        return [edge for edge in self.graph.imports if edge.target == file_path]

    def get_tests_for_file(self, file_path: str) -> list[GraphEdge]:
        return [edge for edge in self.graph.tests if edge.target == file_path or edge.source == file_path]

    def get_docs_for_file(self, file_path: str) -> list[GraphEdge]:
        return [
            edge
            for edge in self.graph.edges
            if edge.edge_type in {EdgeType.DOCUMENTS, EdgeType.MENTIONS}
            and (edge.target == file_path or edge.source == file_path)
        ]

    def get_entrypoints(self) -> list[EntryPointCandidate]:
        return self.graph.entrypoints

    def get_run_commands(self) -> list[str]:
        return self.graph.run_commands

    def get_test_commands(self) -> list[str]:
        return self.graph.test_commands

    def get_build_commands(self) -> list[str]:
        return self.graph.build_commands

    def get_development_workflow(self) -> DevelopmentWorkflowGuide | None:
        return self.graph.development_workflow

    def get_quality_commands(self, command_type: str | None = None) -> list[QualityCommand]:
        if command_type is None:
            return self.graph.quality_commands
        return [command for command in self.graph.quality_commands if command.command_type.value == command_type]

    def get_contributing_rules(self, rule_type: str | None = None) -> list[ContributingRule]:
        if rule_type is None:
            return self.graph.contributing_rules
        return [rule for rule in self.graph.contributing_rules if rule.rule_type.value == rule_type]

    def get_ci_rules(self) -> list[CIRule]:
        return self.graph.ci_rules

    def get_new_contributor_checklist(self) -> list[str]:
        if not self.graph.development_workflow:
            return []
        return self.graph.development_workflow.new_contributor_checklist

    def get_related_context(self, query: str) -> dict[str, list[object]]:
        text = query.lower()
        files = [item for item in self.graph.files if text in item.path.lower() or item.name.lower() in text][:12]
        symbols = [item for item in self.graph.symbols if item.name.lower() in text or text in item.name.lower()][:12]
        edges = [
            edge
            for edge in self.graph.edges
            if text in edge.source.lower() or text in edge.target.lower()
        ][:12]
        return {"files": files, "symbols": symbols, "edges": edges}

    def summary(self) -> dict[str, object]:
        doc_edges = [edge for edge in self.graph.edges if edge.edge_type in {EdgeType.DOCUMENTS, EdgeType.MENTIONS}]
        return {
            "files": len(self.graph.files),
            "symbols": len(self.graph.symbols),
            "imports": len(self.graph.imports),
            "tests": len(self.graph.tests),
            "docs": len(doc_edges),
            "doc_files": len(self.graph.docs),
            "doc_edges": len(doc_edges),
            "build_scripts": len(self.graph.build_scripts),
            "languages": self.graph.languages,
            "primary_language": next(iter(self.graph.languages), ""),
            "core_directories": self.graph.core_directories,
            "key_files": self.graph.key_files[:20],
            "readme_exists": any(item.name.lower().startswith("readme") for item in self.graph.files),
            "quality_commands": len(self.graph.quality_commands),
            "contributing_rules": len(self.graph.contributing_rules),
            "ci_rules": len(self.graph.ci_rules),
            "development_workflow": self._development_workflow_status(),
            "new_contributor_checklist": len(self.get_new_contributor_checklist()),
            "entrypoints": self.graph.entrypoints[:10],
            "setup_commands": self.graph.setup_commands,
            "run_commands": self.graph.run_commands,
            "test_commands": self.graph.test_commands,
            "build_commands": self.graph.build_commands,
            "lint_commands": self.graph.lint_commands,
            "format_commands": self.graph.format_commands,
            "type_check_commands": self.graph.type_check_commands,
        }

    def _dedupe_quality_commands(self, commands: list[QualityCommand]) -> list[QualityCommand]:
        seen: dict[tuple[str, str], QualityCommand] = {}
        confidence_rank = {"low": 1, "medium": 2, "high": 3}
        for command in commands:
            normalized = self._normalize_command(command.command)
            if not normalized:
                continue
            source_file = command.source_file.replace("\\", "/")
            key = (command.command_type.value, normalized)
            sources = set(command.evidence_sources or [])
            sources.add(source_file)
            command.evidence_sources = sorted(source.replace("\\", "/") for source in sources if source)
            existing = seen.get(key)
            if existing is None:
                command.command = normalized
                command.source_file = source_file
                seen[key] = command
                continue
            merged_sources = sorted(set(existing.evidence_sources + command.evidence_sources))
            existing.evidence_sources = merged_sources
            if confidence_rank.get(command.confidence.value, 0) > confidence_rank.get(existing.confidence.value, 0):
                command.command = normalized
                command.source_file = source_file
                command.evidence_sources = merged_sources
                seen[key] = command
        return list(seen.values())

    def _dedupe_contributing_rules(self, rules: list[ContributingRule]) -> list[ContributingRule]:
        seen: dict[tuple[str, str], ContributingRule] = {}
        for rule in rules:
            seen[(rule.description, rule.rule_type.value)] = rule
        return list(seen.values())

    def _merge_language_counts(self, first: dict[str, int], second: dict[str, int]) -> dict[str, int]:
        merged = dict(first)
        for language, count in second.items():
            merged[language] = max(merged.get(language, 0), count)
        return dict(sorted(merged.items(), key=lambda entry: entry[1], reverse=True))

    def _merge_ordered(self, first: list[str], second: list[str]) -> list[str]:
        merged: list[str] = []
        for item in [*first, *second]:
            normalized = self._normalize_command(item) if isinstance(item, str) else item
            if normalized and normalized not in merged:
                merged.append(normalized)
        return merged

    def _merge_entrypoints(self, first: list[EntryPointCandidate], second: list[EntryPointCandidate]) -> list[EntryPointCandidate]:
        confidence_rank = {"low": 1, "medium": 2, "high": 3}
        seen: dict[str, EntryPointCandidate] = {}
        for item in [*first, *second]:
            if not item or not item.path:
                continue
            path = item.path.replace("\\", "/")
            item.path = path
            existing = seen.get(path)
            if existing is None or confidence_rank.get(item.confidence.value, 0) > confidence_rank.get(existing.confidence.value, 0):
                seen[path] = item
        return list(seen.values())

    def _normalize_command(self, command: str) -> str:
        normalized = " ".join(command.replace("\\", "/").strip().split())
        return normalized

    def _development_workflow_status(self) -> str:
        guide = self.graph.development_workflow
        if not guide:
            return "missing"
        has_commands = bool(
            guide.development_commands
            or guide.test_commands
            or guide.lint_commands
            or guide.format_commands
            or guide.type_check_commands
            or guide.build_commands
        )
        has_rules = bool(
            guide.branch_rules
            or guide.commit_rules
            or guide.contribution_rules
            or guide.pull_request_rules
            or guide.ci_rules
            or guide.code_style_rules
            or guide.setup_rules
            or guide.test_rules
        )
        if has_commands and (guide.evidence or has_rules):
            return "ready"
        return "partial"

from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.core.schemas import (
    ChunkDoc,
    CommandType,
    ConfidenceLevel,
    EdgeType,
    EntryPointCandidate,
    FileNode,
    GraphEdge,
    QualityCommand,
    RepoGraphWorkerInput,
    RepoGraphWorkerResult,
    RepoSnapshot,
    RepositoryIntelligenceGraph,
    SourceType,
    WorkerOutput,
    WorkerStatus,
)
from app.services.command_detector import CommandDetector
from app.services.parser_service import ParserService
from app.workers.base_worker import BaseWorker


class RepoGraphWorker(BaseWorker[RepoGraphWorkerInput, RepoGraphWorkerResult]):
    worker_name = "Repo Graph Worker"

    def __init__(self) -> None:
        self.parser = ParserService()
        self.command_detector = CommandDetector()

    def run(self, worker_input: RepoGraphWorkerInput) -> RepoGraphWorkerResult:
        files = self.parser.list_files(worker_input.local_path)
        commands = self.command_detector.detect(worker_input.local_path)
        key_file_names = {
            "README.md",
            "CONTRIBUTING.md",
            "package.json",
            "pyproject.toml",
            "requirements.txt",
            "setup.py",
            "setup.cfg",
            "tox.ini",
            "Dockerfile",
            "Makefile",
            "docker-compose.yml",
        }
        key_files = [
            item.path
            for item in files
            if item.name in key_file_names or item.path.startswith(".github/workflows/")
        ]
        entrypoints = self._detect_entrypoints(files, Path(worker_input.local_path), commands)
        build_scripts = [item for item in files if item.file_type.value == "build"]
        languages = self._language_counts(files)
        core_directories = self._core_directories(files)
        quality_commands = self._quality_commands(commands)
        edges = [
            GraphEdge(
                source=item.path,
                target=command,
                edge_type=EdgeType.BUILDS,
                evidence=f"{item.path} contributes build/run command detection",
                confidence=0.75,
            )
            for item in build_scripts
            for command in commands["build"] + commands["setup"] + commands["run"] + commands["test"]
        ]
        graph = RepositoryIntelligenceGraph(
            files=files,
            docs=[item for item in files if item.file_type.value.startswith("docs")],
            build_scripts=build_scripts,
            edges=edges,
            key_files=key_files,
            languages=languages,
            core_directories=core_directories,
            entrypoints=entrypoints,
            setup_commands=commands["setup"],
            run_commands=commands["run"],
            test_commands=commands["test"],
            build_commands=commands["build"],
            lint_commands=commands["lint"],
            format_commands=commands["format"],
            type_check_commands=commands["type_check"],
            quality_commands=quality_commands,
        )
        snapshot = RepoSnapshot(
            repo_id=worker_input.repo_id,
            repo_url=worker_input.repo_url,
            local_path=worker_input.local_path,
            owner=worker_input.owner,
            name=worker_input.name,
            default_branch=worker_input.default_branch,
            files=files,
            key_files=key_files,
        )
        chunks = self._file_chunks(files)
        output = WorkerOutput(
            worker_name=self.worker_name,
            task="scan files, classify file types, detect key files and commands",
            status=WorkerStatus.SUCCESS if files else WorkerStatus.PARTIAL,
            findings=[
                f"scanned {len(files)} files",
                f"detected {len(key_files)} key files",
                f"detected {len(commands['setup'])} setup commands, {len(commands['run'])} run commands and {len(commands['test'])} test commands",
                f"detected {len(commands['lint'])} lint commands and {len(commands['format'])} format commands",
            ],
            uncertainties=[] if files else ["repository contains no readable files or clone failed"],
            next_actions=["run Symbol Worker", "run Dependency Worker", "run Docs Worker", "run Test Worker"],
        )
        return RepoGraphWorkerResult(repo_snapshot=snapshot, graph=graph, chunks=chunks, worker_output=output)

    def _detect_entrypoints(self, files: list[FileNode], root: Path, commands: dict[str, list[str]]) -> list[EntryPointCandidate]:
        by_path = {item.path.replace("\\", "/"): item for item in files}
        candidates: dict[str, tuple[int, int, EntryPointCandidate]] = {}
        confidence_rank = {ConfidenceLevel.HIGH: 3, ConfidenceLevel.MEDIUM: 2, ConfidenceLevel.LOW: 1}

        def add(path: str, reason: str, source: str, confidence: ConfidenceLevel, priority: int) -> None:
            normalized = path.strip().strip("'\"`").replace("\\", "/").removeprefix("./")
            if normalized not in by_path:
                return
            rank = confidence_rank[confidence]
            item = EntryPointCandidate(path=normalized, reason=reason, source=source, confidence=confidence)
            existing = candidates.get(normalized)
            if existing is None or (priority, -rank, normalized) < (existing[0], -existing[1], normalized):
                candidates[normalized] = (priority, rank, item)

        script_pattern = re.compile(r"(?P<path>(?:\.?[\\/])?(?:[\w.-]+[\\/])*[\w.-]+\.(?:py|js|jsx|ts|tsx))")
        python_module_pattern = re.compile(r"\bpython\s+-m\s+([A-Za-z_][\w.:-]*)")

        for group in ("run", "test", "build", "setup", "lint", "format", "type_check"):
            for command in commands.get(group, []):
                for match in script_pattern.finditer(command):
                    add(match.group("path"), "命令中直接引用的脚本文件", f"{group} command: {command}", ConfidenceLevel.HIGH, 1)
                for module in python_module_pattern.findall(command):
                    for path in self._paths_for_python_module(module):
                        add(path, f"python -m {module} 对应的模块入口", f"{group} command: {command}", ConfidenceLevel.HIGH, 2)

        command_line_pattern = re.compile(
            r"^\s{0,6}(?:\$|>)?\s*(?:python|pip|uv|poetry|pdm|pytest|tox|npm|pnpm|yarn|node|make)\b.*$",
            re.MULTILINE,
        )
        for doc in files:
            if not doc.file_type.value.startswith("docs"):
                continue
            text = self.parser.read_text(root / doc.path)
            for line in command_line_pattern.findall(text):
                for match in script_pattern.finditer(line):
                    add(match.group("path"), "README/docs 运行命令中引用的脚本文件", doc.path, ConfidenceLevel.HIGH, 1)
                for module in python_module_pattern.findall(line):
                    for path in self._paths_for_python_module(module):
                        add(path, f"README/docs 中 python -m {module} 对应的模块入口", doc.path, ConfidenceLevel.HIGH, 2)

        for item in files:
            parts = Path(item.path).parts
            if item.name == "__main__.py":
                priority = 2 if parts and parts[0] == "src" else 3
                confidence = ConfidenceLevel.HIGH if parts and parts[0] == "src" else ConfidenceLevel.MEDIUM
                add(item.path, "Python 包执行入口 __main__.py", item.path, confidence, priority)

        common_names = {"app.py", "main.py", "server.py", "cli.py", "index.js", "app.js", "server.js"}
        for item in files:
            if item.name in common_names:
                add(item.path, "常见应用入口文件名", item.path, ConfidenceLevel.MEDIUM, 3)

        package_json = root / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
            for field in ("main", "module"):
                value = data.get(field)
                if isinstance(value, str):
                    add(value, f"package.json {field} 字段指定入口", "package.json", ConfidenceLevel.HIGH, 4)
            bin_value = data.get("bin")
            if isinstance(bin_value, str):
                add(bin_value, "package.json bin 字段指定入口", "package.json", ConfidenceLevel.HIGH, 4)
            elif isinstance(bin_value, dict):
                for value in bin_value.values():
                    if isinstance(value, str):
                        add(value, "package.json bin 字段指定入口", "package.json", ConfidenceLevel.HIGH, 4)
            scripts = data.get("scripts", {})
            if isinstance(scripts, dict):
                for script_name, script_body in scripts.items():
                    if not isinstance(script_body, str):
                        continue
                    for match in script_pattern.finditer(script_body):
                        add(match.group("path"), f"package.json scripts.{script_name} 引用脚本", "package.json", ConfidenceLevel.MEDIUM, 4)

        for item in files:
            parts = Path(item.path).parts
            if item.name == "__init__.py" and parts and parts[0] == "src" and len(parts) <= 3:
                add(item.path, "__init__.py 仅作为 Python package entry，不作为主流程入口", item.path, ConfidenceLevel.LOW, 5)

        return [item for _, _, item in sorted(candidates.values(), key=lambda entry: (entry[0], -entry[1], entry[2].path))[:20]]

    def _paths_for_python_module(self, module: str) -> list[str]:
        module = module.split(":")[0].strip(".")
        if not module:
            return []
        module_path = module.replace(".", "/")
        return [
            f"src/{module_path}/__main__.py",
            f"src/{module_path}.py",
            f"{module_path}/__main__.py",
            f"{module_path}.py",
        ]

    def _language_counts(self, files: list) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in files:
            if not item.language or item.language == "unknown":
                continue
            counts[item.language] = counts.get(item.language, 0) + 1
        return dict(sorted(counts.items(), key=lambda entry: entry[1], reverse=True))

    def _core_directories(self, files: list) -> list[str]:
        counts: dict[str, int] = {}
        for item in files:
            root = Path(item.path).parts[0] if Path(item.path).parts else ""
            if not root or "." in root:
                continue
            counts[root] = counts.get(root, 0) + 1
        return [name for name, _ in sorted(counts.items(), key=lambda entry: entry[1], reverse=True)[:8]]

    def _quality_commands(self, commands: dict[str, list[str]]) -> list[QualityCommand]:
        command_types = {
            "run": CommandType.DEV,
            "setup": CommandType.SETUP,
            "test": CommandType.TEST,
            "build": CommandType.BUILD,
            "lint": CommandType.LINT,
            "format": CommandType.FORMAT,
            "type_check": CommandType.TYPE_CHECK,
        }
        quality_commands: list[QualityCommand] = []
        for group, command_type in command_types.items():
            for command in commands.get(group, []):
                quality_commands.append(
                    QualityCommand(
                        name=command.split()[0] if command.split() else group,
                        command=command,
                        command_type=command_type,
                        source_file="deterministic repository scan",
                        confidence=ConfidenceLevel.MEDIUM,
                        evidence_sources=["deterministic repository scan"],
                    )
                )
        return quality_commands

    def _file_chunks(self, files: list) -> list[ChunkDoc]:
        chunks: list[ChunkDoc] = []
        for item in files:
            if not item.content_preview:
                continue
            source_type = SourceType.CODE
            if item.file_type.value.startswith("docs"):
                source_type = SourceType.DOCS
            elif item.file_type.value == "test":
                source_type = SourceType.TEST
            elif item.file_type.value == "config":
                source_type = SourceType.CONFIG
            elif item.file_type.value == "build":
                source_type = SourceType.BUILD
            chunks.append(
                ChunkDoc(
                    chunk_id=str(uuid5(NAMESPACE_URL, f"file:{item.path}")),
                    source_type=source_type,
                    file_path=item.path,
                    title=item.name,
                    text=item.content_preview,
                    line_start=1,
                    line_end=min(item.line_count or 1, 80),
                    metadata={"language": item.language, "file_type": item.file_type.value},
                )
            )
        return chunks

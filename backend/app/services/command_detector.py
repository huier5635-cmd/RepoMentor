from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path


class CommandDetector:
    def detect(self, local_path: str) -> dict[str, list[str]]:
        root = Path(local_path)
        commands = {"setup": [], "run": [], "test": [], "build": [], "lint": [], "format": [], "type_check": []}
        self._from_package_json(root / "package.json", commands)
        self._from_pyproject(root / "pyproject.toml", commands)
        self._from_makefile(root / "Makefile", commands)
        self._from_readme(root, commands)
        self._from_workflows(root / ".github" / "workflows", commands)
        return {key: self._prioritize_commands(key, value) for key, value in commands.items()}

    def _from_package_json(self, path: Path, commands: dict[str, list[str]]) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        scripts = data.get("scripts", {})
        if not isinstance(scripts, dict):
            return
        for name in scripts:
            command = f"npm run {name}" if name not in {"start", "test"} else f"npm {name}"
            lowered = name.lower()
            self._append_classified(commands, lowered, command)

    def _from_pyproject(self, path: Path, commands: dict[str, list[str]]) -> None:
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8", errors="ignore")
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            data = {}
        commands["setup"].append("pip install -e .")
        tool = data.get("tool", {}) if isinstance(data, dict) else {}
        if "[tool.pytest" in text or "pytest" in text or "pytest" in tool:
            commands["test"].append("pytest")
            commands["test"].append("python -m pytest")
        if "ruff" in tool:
            commands["lint"].append("ruff check .")
        if "black" in tool:
            commands["format"].append("black .")
        if "mypy" in tool:
            commands["type_check"].append("mypy .")
        scripts = data.get("project", {}).get("scripts", {}) if isinstance(data, dict) else {}
        if isinstance(scripts, dict):
            for script_name in scripts:
                commands["run"].append(f"python -m {script_name}")

    def _from_makefile(self, path: Path, commands: dict[str, list[str]]) -> None:
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8", errors="ignore")
        for target in re.findall(r"^([A-Za-z0-9_\-]+):", text, flags=re.MULTILINE):
            command = f"make {target}"
            lowered = target.lower()
            self._append_classified(commands, lowered, command)

    def _from_readme(self, root: Path, commands: dict[str, list[str]]) -> None:
        readme = next((path for path in [root / "README.md", root / "readme.md"] if path.exists()), None)
        if not readme:
            return
        text = readme.read_text(encoding="utf-8", errors="ignore")
        for line in self._command_lines_from_markdown(text):
            clean = self._clean_command(line)
            if clean:
                self._append_classified(commands, clean.lower(), clean)

    def _from_workflows(self, path: Path, commands: dict[str, list[str]]) -> None:
        if not path.exists():
            return
        for workflow in list(path.glob("*.yml")) + list(path.glob("*.yaml")):
            text = workflow.read_text(encoding="utf-8", errors="ignore")
            for command in re.findall(r"(?m)^\s*run:\s*(.+)$", text):
                self._append_classified(commands, command.lower(), command.strip())

    def _append_classified(self, commands: dict[str, list[str]], text: str, command: str) -> None:
        if any(token in text for token in ["install", "sync", "setup", "bootstrap"]):
            commands["setup"].append(command)
        elif any(token in text for token in ["test", "pytest", "jest", "vitest", "coverage", "tox"]):
            commands["test"].append(command)
        elif any(token in text for token in ["lint", "ruff check", "flake8", "eslint"]):
            commands["lint"].append(command)
        elif any(token in text for token in ["format", "black", "prettier", "ruff format"]):
            commands["format"].append(command)
        elif any(token in text for token in ["mypy", "pyright", "tsc", "typecheck", "type-check"]):
            commands["type_check"].append(command)
        elif "build" in text:
            commands["build"].append(command)
        elif any(token in text for token in ["start", "dev", "serve", "preview", "run", "uvicorn"]):
            commands["run"].append(command)

    def _command_lines_from_markdown(self, text: str) -> list[str]:
        lines: list[str] = []
        for block in re.findall(r"```[^\n`]*\n(.*?)```", text, flags=re.DOTALL):
            lines.extend(block.splitlines())
        for match in re.finditer(
            r"(?m)^\s*(?:\$|>)\s*((?:python|pip|uv|poetry|pdm|npm|pnpm|yarn|pytest|tox|ruff|black|flake8|mypy|pyright|eslint|prettier|tsc|uvicorn|make|docker|docker-compose)\b[^\n`]*)$",
            text,
        ):
            lines.append(match.group(1))
        return lines

    def _clean_command(self, line: str) -> str:
        command = line.strip().removeprefix("$").strip()
        if not command or command.startswith("#"):
            return ""
        if not re.match(r"^(python|pip|uv|poetry|pdm|npm|pnpm|yarn|pytest|tox|ruff|black|flake8|mypy|pyright|eslint|prettier|tsc|uvicorn|make|docker|docker-compose)\b", command):
            return ""
        if command.startswith("make ") and command.split()[1:2] in (["sure"], ["changes"]):
            return ""
        return command

    def _prioritize_commands(self, group: str, values: list[str]) -> list[str]:
        unique = list(dict.fromkeys(value for value in values if value.strip()))

        def priority(command: str) -> tuple[int, str]:
            lowered = command.lower()
            if group == "setup":
                if lowered == "pip install -e .":
                    return (0, lowered)
                if "requirements" in lowered:
                    return (1, lowered)
                if lowered in {"npm install", "pnpm install", "yarn install"}:
                    return (2, lowered)
                if ".[test]" in lowered or ".[dev]" in lowered:
                    return (3, lowered)
                return (10, lowered)
            if group == "test":
                if lowered == "pytest":
                    return (0, lowered)
                if lowered == "python -m pytest":
                    return (1, lowered)
                return (10, lowered)
            if group == "run":
                if "flask" in lowered or "uvicorn" in lowered or "npm start" in lowered:
                    return (0, lowered)
                return (10, lowered)
            return (0, lowered)

        return sorted(unique, key=priority)

from __future__ import annotations

import ast
import re
from pathlib import Path

from app.core.config import get_settings
from app.core.schemas import FileNode, FileType, GraphEdge, EdgeType, SymbolNode, SymbolType


LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".json": "json",
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".toml": "toml",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".css": "css",
    ".html": "html",
    ".jsonl": "jsonl",
    ".bib": "bibtex",
    ".txt": "text",
    ".cfg": "config",
    ".ini": "config",
    ".sh": "shell",
}

TEXT_EXTENSIONS = {
    "",
    ".cfg",
    ".css",
    ".html",
    ".bib",
    ".ini",
    ".example",
    ".js",
    ".json",
    ".jsonl",
    ".jsx",
    ".md",
    ".py",
    ".rst",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".repomentor_cache",
    "dist",
    "build",
}

IGNORED_FILES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
}

SENSITIVE_NAME_TOKENS = {
    "secret",
    "secrets",
    "private",
    "credential",
    "credentials",
    "token",
    "tokens",
}

IGNORED_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}


class ParserService:
    def list_files(self, local_path: str) -> list[FileNode]:
        root = Path(local_path)
        settings = get_settings()
        files: list[FileNode] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if len(files) >= settings.max_repo_files:
                break
            rel_path = path.relative_to(root).as_posix()
            if any(part in IGNORED_DIRS for part in Path(rel_path).parts):
                continue
            if self.is_sensitive_file(path):
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > settings.max_file_size_bytes:
                continue
            preview = ""
            line_count = 0
            if size <= settings.max_file_size_bytes and self.is_text_file(path):
                text = self.read_text(path)
                preview = text[: settings.max_preview_chars]
                line_count = text.count("\n") + (1 if text else 0)
            files.append(
                FileNode(
                    path=rel_path,
                    name=path.name,
                    extension=path.suffix,
                    language=self.detect_language(path),
                    file_type=self.classify_file(rel_path, path),
                    size=size,
                    content_preview=preview,
                    line_count=line_count,
                )
            )
        return sorted(files, key=lambda item: item.path)

    def detect_language(self, path: Path) -> str:
        return LANGUAGE_BY_EXTENSION.get(path.suffix.lower(), "unknown")

    def is_sensitive_file(self, path: Path) -> bool:
        name = path.name.lower()
        if name == ".env.example":
            return False
        stem = path.stem.lower()
        return (
            name in IGNORED_FILES
            or name.startswith(".env.")
            or path.suffix.lower() in IGNORED_SUFFIXES
            or any(token in stem for token in SENSITIVE_NAME_TOKENS)
        )

    def classify_file(self, rel_path: str, path: Path) -> FileType:
        lowered = rel_path.lower()
        name = path.name.lower()
        suffix = path.suffix.lower()
        if self.is_test_path(lowered):
            return FileType.TEST
        if name.startswith("readme") and suffix in {".md", ".rst", ".txt"}:
            return FileType.DOCS
        if name.startswith("license") or name in {"copying", "notice"}:
            return FileType.DOCS_LEGAL
        if lowered.endswith(".bib"):
            return FileType.DOCS_REFERENCE if lowered.startswith(("docs/", "doc/")) else FileType.DATA
        if suffix == ".html":
            return FileType.DOCS_STATIC if lowered.startswith(("docs/", "doc/")) else FileType.SOURCE_FRONTEND
        if suffix == ".css":
            return FileType.SOURCE_FRONTEND_STYLE
        if suffix == ".jsonl":
            return FileType.DATA
        if suffix == ".json":
            if lowered.startswith(("data/", "datasets/", "results/", "reports/", "benchmarks/")):
                return FileType.DATA
            return FileType.CONFIG
        if name in {".env.example", ".gitignore", ".gitattributes", ".dockerignore"}:
            return FileType.CONFIG
        if (name in {"contributing.md", "changelog.md"} or lowered.startswith(("docs/", "doc/", "examples/"))) and self.is_text_file(path):
            return FileType.DOCS
        if name in {"dockerfile", "makefile"} or lowered.startswith(".github/workflows/"):
            return FileType.BUILD
        if name in {
            "package.json",
            "pyproject.toml",
            "requirements.txt",
            "setup.py",
            "setup.cfg",
            "tox.ini",
            ".pre-commit-config.yaml",
            "vite.config.js",
            "vite.config.ts",
        }:
            return FileType.CONFIG
        if path.suffix.lower() in {".py", ".js", ".jsx", ".ts", ".tsx"}:
            return FileType.SOURCE
        return FileType.UNKNOWN

    def is_test_path(self, lowered_path: str) -> bool:
        name = Path(lowered_path).name
        return (
            lowered_path.startswith("tests/")
            or "/tests/" in lowered_path
            or name.startswith("test_")
            or name.endswith((".test.js", ".test.jsx", ".test.ts", ".test.tsx"))
            or name.endswith((".spec.js", ".spec.jsx", ".spec.ts", ".spec.tsx"))
        )

    def read_text(self, path: Path) -> str:
        if not self.is_text_file(path):
            return ""
        for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
            except OSError:
                return ""
        return ""

    def is_text_file(self, path: Path) -> bool:
        return path.suffix.lower() in TEXT_EXTENSIONS or path.name.lower() in {"dockerfile", "makefile"}

    def parse_symbols(self, local_path: str, file_node: FileNode) -> tuple[list[SymbolNode], list[GraphEdge]]:
        path = Path(local_path) / file_node.path
        if file_node.language == "python":
            return self._parse_python_symbols(path, file_node.path)
        if file_node.language in {"javascript", "typescript"}:
            return self._parse_js_symbols(path, file_node.path, file_node.language)
        return [], []

    def parse_imports(self, local_path: str, file_node: FileNode) -> tuple[list[GraphEdge], list[str]]:
        path = Path(local_path) / file_node.path
        if file_node.language == "python":
            return self._parse_python_imports(path, file_node.path, local_path)
        if file_node.language in {"javascript", "typescript"}:
            return self._parse_js_imports(path, file_node.path, local_path)
        return [], []

    def _parse_python_symbols(self, path: Path, rel_path: str) -> tuple[list[SymbolNode], list[GraphEdge]]:
        text = self.read_text(path)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return [], []
        symbols: list[SymbolNode] = []
        edges: list[GraphEdge] = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                symbol = SymbolNode(
                    name=node.name,
                    symbol_type=SymbolType.CLASS,
                    file_path=rel_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    signature=f"class {node.name}",
                    docstring=ast.get_docstring(node) or "",
                    language="python",
                )
                symbols.append(symbol)
                edges.append(self._defines_edge(rel_path, symbol))
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method = SymbolNode(
                            name=f"{node.name}.{child.name}",
                            symbol_type=SymbolType.METHOD,
                            file_path=rel_path,
                            line_start=child.lineno,
                            line_end=getattr(child, "end_lineno", child.lineno),
                            signature=self._python_signature(child, owner=node.name),
                            docstring=ast.get_docstring(child) or "",
                            language="python",
                        )
                        symbols.append(method)
                        edges.append(self._defines_edge(rel_path, method))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbol = SymbolNode(
                    name=node.name,
                    symbol_type=SymbolType.FUNCTION,
                    file_path=rel_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    signature=self._python_signature(node),
                    docstring=ast.get_docstring(node) or "",
                    language="python",
                )
                symbols.append(symbol)
                edges.append(self._defines_edge(rel_path, symbol))
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        symbol = SymbolNode(
                            name=target.id,
                            symbol_type=SymbolType.CONSTANT,
                            file_path=rel_path,
                            line_start=node.lineno,
                            line_end=getattr(node, "end_lineno", node.lineno),
                            signature=target.id,
                            language="python",
                        )
                        symbols.append(symbol)
                        edges.append(self._defines_edge(rel_path, symbol))
        return symbols, edges

    def _parse_js_symbols(self, path: Path, rel_path: str, language: str) -> tuple[list[SymbolNode], list[GraphEdge]]:
        text = self.read_text(path)
        patterns = [
            (SymbolType.CLASS, re.compile(r"(?:export\s+)?class\s+([A-Za-z_$][\w$]*)")),
            (SymbolType.FUNCTION, re.compile(r"(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(")),
            (SymbolType.FUNCTION, re.compile(r"(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>")),
            (SymbolType.VARIABLE, re.compile(r"(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*=")),
            (SymbolType.INTERFACE, re.compile(r"(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)")),
        ]
        symbols: list[SymbolNode] = []
        edges: list[GraphEdge] = []
        lines = text.splitlines()
        for symbol_type, pattern in patterns:
            for match in pattern.finditer(text):
                name = match.group(1)
                line_start = text[: match.start()].count("\n") + 1
                signature = lines[line_start - 1].strip() if line_start - 1 < len(lines) else name
                symbol = SymbolNode(
                    name=name,
                    symbol_type=symbol_type,
                    file_path=rel_path,
                    line_start=line_start,
                    line_end=line_start,
                    signature=signature[:240],
                    language=language,
                )
                symbols.append(symbol)
                edges.append(self._defines_edge(rel_path, symbol))
        dedup: dict[tuple[str, int], SymbolNode] = {}
        for symbol in symbols:
            dedup[(symbol.name, symbol.line_start)] = symbol
        return list(dedup.values()), edges

    def _parse_python_imports(self, path: Path, rel_path: str, local_path: str) -> tuple[list[GraphEdge], list[str]]:
        text = self.read_text(path)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return [], []
        edges: list[GraphEdge] = []
        unresolved: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                prefix = "." * node.level
                names = [f"{prefix}{node.module or alias.name}" for alias in node.names]
            else:
                continue
            for module_name in names:
                target = self.resolve_python_import(local_path, rel_path, module_name)
                if target:
                    edges.append(
                        GraphEdge(
                            source=rel_path,
                            target=target,
                            edge_type=EdgeType.IMPORTS,
                            evidence=f"line {getattr(node, 'lineno', 1)}: import {module_name}",
                            confidence=0.9,
                        )
                    )
                else:
                    unresolved.append(f"{rel_path}: {module_name}")
        return edges, unresolved

    def _parse_js_imports(self, path: Path, rel_path: str, local_path: str) -> tuple[list[GraphEdge], list[str]]:
        text = self.read_text(path)
        pattern = re.compile(r"(?:import\s+.*?\s+from\s+|import\s*\(|require\s*\()\s*['\"]([^'\"]+)['\"]")
        edges: list[GraphEdge] = []
        unresolved: list[str] = []
        for match in pattern.finditer(text):
            module_name = match.group(1)
            target = self.resolve_js_import(local_path, rel_path, module_name)
            line_no = text[: match.start()].count("\n") + 1
            if target:
                edges.append(
                    GraphEdge(
                        source=rel_path,
                        target=target,
                        edge_type=EdgeType.IMPORTS,
                        evidence=f"line {line_no}: import {module_name}",
                        confidence=0.85,
                    )
                )
            else:
                unresolved.append(f"{rel_path}: {module_name}")
        return edges, unresolved

    def resolve_python_import(self, local_path: str, rel_path: str, module_name: str) -> str | None:
        root = Path(local_path)
        if module_name.startswith("."):
            level = len(module_name) - len(module_name.lstrip("."))
            module_tail = module_name.lstrip(".")
            base = Path(rel_path).parent
            for _ in range(max(0, level - 1)):
                base = base.parent
            candidate = base / module_tail.replace(".", "/")
        else:
            candidate = Path(module_name.replace(".", "/"))
        for suffix in (".py", "/__init__.py"):
            target = root / f"{candidate.as_posix()}{suffix}"
            if target.exists():
                return target.relative_to(root).as_posix()
        return None

    def resolve_js_import(self, local_path: str, rel_path: str, module_name: str) -> str | None:
        if not module_name.startswith("."):
            return None
        root = Path(local_path)
        base = (root / rel_path).parent / module_name
        candidates = [base] + [Path(f"{base}{suffix}") for suffix in (".js", ".jsx", ".ts", ".tsx", ".json")]
        candidates.extend(base / f"index{suffix}" for suffix in (".js", ".jsx", ".ts", ".tsx"))
        for target in candidates:
            if target.exists() and target.is_file():
                return target.relative_to(root).as_posix()
        return None

    def _python_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef, owner: str | None = None) -> str:
        args = [arg.arg for arg in node.args.args]
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        name = f"{owner}.{node.name}" if owner else node.name
        return f"{prefix} {name}({', '.join(args)})"

    def _defines_edge(self, rel_path: str, symbol: SymbolNode) -> GraphEdge:
        return GraphEdge(
            source=rel_path,
            target=f"{symbol.file_path}::{symbol.name}",
            edge_type=EdgeType.DEFINES,
            evidence=f"{symbol.symbol_type.value} {symbol.name} at {symbol.file_path}:{symbol.line_start}",
            confidence=1.0,
        )

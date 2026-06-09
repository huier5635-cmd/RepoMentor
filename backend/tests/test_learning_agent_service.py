from __future__ import annotations

from pathlib import Path

from app.core.schemas import (
    CommandType,
    ConfidenceLevel,
    EdgeType,
    EntryPointCandidate,
    FileNode,
    FileType,
    GraphEdge,
    QualityCommand,
    RepoSnapshot,
    RepositoryIntelligenceGraph,
    RepositoryRecord,
    SymbolNode,
)
from app.services.learning_agent_service import LearningAgentService


class DummyStore:
    def __init__(self, record: RepositoryRecord) -> None:
        self.record = record

    def load(self, repo_id: str) -> RepositoryRecord:
        assert repo_id == self.record.repo_id
        return self.record


def test_learning_agent_generates_v2_artifacts(tmp_path: Path):
    record = _record(tmp_path)
    service = LearningAgentService(DummyStore(record))

    path = service.learning_path_v2("r1")
    assert len(path.steps) == 8
    assert "RepositoryIntelligenceGraph" in " ".join(path.hallucination_guardrails)
    assert all(file in {item.path for item in record.graph.files} for step in path.steps for file in step.concrete_files)

    tour = service.architecture_tour("r1")
    assert tour.entry_points[0].path == "scripts/run_demo.py"
    assert tour.major_components
    maintainer_tour = service.architecture_tour("r1", audience="maintainer")
    assert any("维护者" in item for item in maintainer_tour.key_invariants)

    cards = service.module_study_cards("r1")
    assert cards
    assert cards[0].module_path in {"scripts/run_demo.py", "src/demo_app.py"}
    contributor_cards = service.module_study_cards("r1", audience="contributor")
    assert any("贡献者" in card.role_in_system for card in contributor_cards)


def test_internal_tasks_onboarding_and_change_impact(tmp_path: Path):
    record = _record(tmp_path)
    service = LearningAgentService(DummyStore(record))

    funnel = service.contribution_funnel("r1")
    assert funnel.issues
    assert all(issue.source == "internal_suggestion" for issue in funnel.issues)
    assert all(issue.is_github_issue is False for issue in funnel.issues)
    assert any(issue.task_type == "tests" for issue in funnel.issues)

    debt = service.onboarding_debt("r1")
    assert debt.has_readme is True
    assert debt.has_test_entry is True
    assert debt.has_contributing is False
    assert debt.recommended_maintainer_actions

    impact = service.change_impact("r1", request=type("Req", (), {"file_path": "src/demo_app.py", "symbol": ""})())
    assert "tests/test_demo_app.py" in impact.likely_affected_tests
    assert "python -m pytest tests" in impact.must_run_commands


def test_bilingual_doc_view_preserves_commands_and_paths(tmp_path: Path):
    record = _record(tmp_path)
    service = LearningAgentService(DummyStore(record))

    view = service.bilingual_doc_view("r1")
    tokens = {token for chunk in view.chunks for token in chunk.preserved_tokens}
    assert "pip install -r requirements.txt" in tokens
    assert "scripts/run_demo.py" in tokens
    assert view.chunks[0].source_file == "README.md"
    assert view.chunks[0].source_chunk_hash
    assert view.chunks[0].target_lang == "zh-CN"
    assert view.chunks[0].translated_text == view.chunks[0].zh_text
    assert view.chunks[0].stale_status in {"fresh", "unknown_commit"}
    assert view.fidelity_warnings

    glossary_terms = service.glossary("r1").terms
    assert any(term.category == "symbol" and term.term == "run" for term in glossary_terms)


def _record(tmp_path: Path) -> RepositoryRecord:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        "# Demo Agent\n\n```bash\npip install -r requirements.txt\npython scripts/run_demo.py\npython -m pytest tests\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "scripts" / "run_demo.py").write_text("from src.demo_app import run\nrun()\n", encoding="utf-8")
    (tmp_path / "src" / "demo_app.py").write_text("def run():\n    return 'ok'\n", encoding="utf-8")
    (tmp_path / "tests" / "test_demo_app.py").write_text("from src.demo_app import run\n\ndef test_run():\n    assert run() == 'ok'\n", encoding="utf-8")
    (tmp_path / "docs" / "architecture.md").write_text("# Architecture\nscripts/run_demo.py calls src/demo_app.py\n", encoding="utf-8")
    files = [
        FileNode(path="README.md", name="README.md", extension=".md", language="markdown", file_type=FileType.DOCS, content_preview="# Demo Agent\npip install -r requirements.txt\npython scripts/run_demo.py\npython -m pytest tests"),
        FileNode(path="scripts/run_demo.py", name="run_demo.py", extension=".py", language="python", file_type=FileType.SOURCE, content_preview="from src.demo_app import run"),
        FileNode(path="src/demo_app.py", name="demo_app.py", extension=".py", language="python", file_type=FileType.SOURCE, content_preview="def run(): return 'ok'"),
        FileNode(path="tests/test_demo_app.py", name="test_demo_app.py", extension=".py", language="python", file_type=FileType.TEST, content_preview="from src.demo_app import run"),
        FileNode(path="docs/architecture.md", name="architecture.md", extension=".md", language="markdown", file_type=FileType.DOCS, content_preview="scripts/run_demo.py calls src/demo_app.py"),
    ]
    graph = RepositoryIntelligenceGraph(
        files=files,
        docs=[files[0], files[4]],
        symbols=[SymbolNode(name="run", symbol_type="function", file_path="src/demo_app.py")],
        imports=[GraphEdge(source="scripts/run_demo.py", target="src/demo_app.py", edge_type=EdgeType.IMPORTS)],
        tests=[GraphEdge(source="tests/test_demo_app.py", target="src/demo_app.py", edge_type=EdgeType.TESTS)],
        edges=[
            GraphEdge(source="scripts/run_demo.py", target="src/demo_app.py", edge_type=EdgeType.IMPORTS),
            GraphEdge(source="tests/test_demo_app.py", target="src/demo_app.py", edge_type=EdgeType.TESTS),
            GraphEdge(source="docs/architecture.md", target="src/demo_app.py", edge_type=EdgeType.DOCUMENTS),
        ],
        entrypoints=[EntryPointCandidate(path="scripts/run_demo.py", reason="README command", source="README.md", confidence=ConfidenceLevel.HIGH)],
        core_directories=["src", "scripts", "tests", "docs"],
        setup_commands=["pip install -r requirements.txt"],
        run_commands=["python scripts/run_demo.py"],
        test_commands=["python -m pytest tests"],
        quality_commands=[
            QualityCommand(name="install", command="pip install -r requirements.txt", command_type=CommandType.SETUP, source_file="README.md", evidence_sources=["README.md"]),
            QualityCommand(name="demo", command="python scripts/run_demo.py", command_type=CommandType.DEV, source_file="README.md", evidence_sources=["README.md"]),
            QualityCommand(name="test", command="python -m pytest tests", command_type=CommandType.TEST, source_file="README.md", evidence_sources=["README.md"]),
        ],
    )
    snapshot = RepoSnapshot(repo_id="r1", repo_url=str(tmp_path), local_path=str(tmp_path), files=files)
    return RepositoryRecord(repo_id="r1", snapshot=snapshot, graph=graph)

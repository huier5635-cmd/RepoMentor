from app.answer.candidate_answer_generator import CandidateAnswerGenerator
from app.answer.evidence_builder import EvidenceBuilder
from app.core.schemas import (
    CommandType,
    ConfidenceLevel,
    EntryPointCandidate,
    EvidenceItem,
    FileNode,
    FileType,
    QualityCommand,
    RepositoryIntelligenceGraph,
    SharedWorkingMemory,
    SourceType,
    SymbolNode,
    SymbolType,
    TaskType,
)


def sample_graph() -> RepositoryIntelligenceGraph:
    files = [
        FileNode(path="README.md", name="README.md", file_type=FileType.DOCS, language="markdown", content_preview="Repo demo quick start", line_count=10),
        FileNode(path="docs/architecture.md", name="architecture.md", file_type=FileType.DOCS, language="markdown", content_preview="Architecture overview", line_count=8),
        FileNode(path="src/app.py", name="app.py", file_type=FileType.SOURCE, language="python", content_preview="def main(): pass", line_count=2),
        FileNode(path="src/core.py", name="core.py", file_type=FileType.SOURCE, language="python", content_preview="class Core: pass", line_count=2),
        FileNode(path="tests/test_core.py", name="test_core.py", file_type=FileType.TEST, language="python", content_preview="def test_core(): pass", line_count=2),
    ]
    return RepositoryIntelligenceGraph(
        files=files,
        docs=[files[0], files[1]],
        symbols=[
            SymbolNode(name="main", symbol_type=SymbolType.FUNCTION, file_path="src/app.py"),
            SymbolNode(name="Core", symbol_type=SymbolType.CLASS, file_path="src/core.py"),
        ],
        core_directories=["src"],
        entrypoints=[EntryPointCandidate(path="src/app.py", reason="common app entry", source="app.py", confidence=ConfidenceLevel.MEDIUM)],
        test_commands=["python -m pytest tests"],
        quality_commands=[
            QualityCommand(
                name="test",
                command="python -m pytest tests",
                command_type=CommandType.TEST,
                source_file="README.md",
                evidence_sources=["README.md"],
            )
        ],
    )


def test_overview_has_readme_evidence():
    evidence = EvidenceBuilder().build_repo_overview_evidence(sample_graph())
    assert any(item.source_type == SourceType.DOCS and item.file_path == "README.md" for item in evidence)


def test_core_modules_has_graph_and_code_evidence():
    evidence = EvidenceBuilder().build_core_modules_evidence(sample_graph(), sample_graph().symbols)
    assert any(item.source_type == SourceType.GRAPH for item in evidence)
    assert any(item.source_type == SourceType.CODE and item.file_path in {"src/app.py", "src/core.py"} for item in evidence)


def test_entrypoints_has_code_evidence():
    evidence = EvidenceBuilder().build_entrypoints_evidence(sample_graph())
    assert any(item.source_type == SourceType.CODE and item.file_path == "src/app.py" for item in evidence)


def test_docs_recommendation_has_docs_evidence():
    evidence = EvidenceBuilder().build_docs_recommendation_evidence([], sample_graph())
    assert any(item.source_type == SourceType.DOCS for item in evidence)


def test_learning_path_evidence_contains_required_sources():
    evidence = EvidenceBuilder().build_learning_path_evidence(sample_graph(), [])
    source_types = {item.source_type for item in evidence}
    assert SourceType.DOCS in source_types
    assert SourceType.COMMAND in source_types
    assert SourceType.CODE in source_types or SourceType.GRAPH in source_types
    assert SourceType.TEST in source_types


def test_internal_first_tasks_have_evidence():
    evidence = EvidenceBuilder().build_issue_or_internal_task_evidence([], sample_graph())
    assert any(item.source_type == SourceType.INTERNAL_SUGGESTION for item in evidence)


def test_candidate_core_modules_answer_keeps_evidence():
    graph = sample_graph()
    memory = SharedWorkingMemory(session_id="s1", current_task="code_explanation", user_question="核心模块有哪些？")
    answer = CandidateAnswerGenerator().generate(TaskType.CODE_EXPLANATION, memory, graph)
    assert answer.answer_type == "core_modules"
    assert answer.evidence
    assert any(item.source_type in {SourceType.CODE, SourceType.GRAPH} for item in answer.evidence)

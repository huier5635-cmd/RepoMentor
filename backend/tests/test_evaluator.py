from app.answer.evaluator import Evaluator
from app.core.schemas import (
    AnswerBundle,
    EvidenceItem,
    FileNode,
    FileType,
    RepositoryIntelligenceGraph,
    SourceType,
)


def evidence(source_type: SourceType = SourceType.DOCS, file_path: str = "README.md") -> EvidenceItem:
    return EvidenceItem(
        evidence_id=f"e-{source_type.value}-{file_path}",
        source_type=source_type,
        source_ref=file_path,
        file_path=file_path,
        quote="evidence",
        supports_claim="test evidence",
    )


def graph() -> RepositoryIntelligenceGraph:
    return RepositoryIntelligenceGraph(
        files=[
            FileNode(path="README.md", name="README.md", file_type=FileType.DOCS),
            FileNode(path="src/app.py", name="app.py", file_type=FileType.SOURCE),
        ]
    )


def test_missing_evidence_fails():
    report = Evaluator().evaluate(AnswerBundle(conclusion="这个仓库有清晰结论。", answer_type="overview"), graph())
    assert report.passed is False
    assert report.missing_evidence


def test_missing_contributing_is_uncertainty_not_hallucination():
    bundle = AnswerBundle(
        conclusion="未找到 CONTRIBUTING.md，贡献流程只能从 README 推断。",
        answer_type="development_workflow",
        evidence=[evidence(SourceType.WORKFLOW, "README.md")],
        steps=["未找到 CONTRIBUTING.md。"],
    )
    report = Evaluator().evaluate(bundle, graph())
    assert "CONTRIBUTING.md" in report.missing_file_uncertainty
    assert not report.hallucinated_file


def test_missing_lint_command_is_uncertainty_not_hallucination():
    bundle = AnswerBundle(
        conclusion="未找到 lint 命令。",
        answer_type="development_workflow",
        evidence=[evidence(SourceType.WORKFLOW, "README.md")],
        steps=["未找到 lint 命令或 lint 脚本。"],
    )
    report = Evaluator().evaluate(bundle, graph())
    assert not report.hallucinated_command
    assert "lint" in report.missing_command_uncertainty


def test_fabricated_file_is_hallucination():
    bundle = AnswerBundle(
        conclusion="请阅读 src/missing.py。",
        evidence=[evidence()],
        steps=["阅读 src/missing.py"],
    )
    report = Evaluator().evaluate(bundle, graph())
    assert report.passed is False
    assert "src/missing.py" in report.hallucinated_file


def test_existing_basename_is_not_hallucination():
    repo_graph = RepositoryIntelligenceGraph(
        files=[FileNode(path="src/__init__.py", name="__init__.py", file_type=FileType.SOURCE)]
    )
    bundle = AnswerBundle(
        conclusion="__init__.py 只是低置信 package entry。",
        evidence=[evidence(SourceType.GRAPH, "RepositoryGraph summary")],
        answer_type="entrypoints",
    )
    report = Evaluator().evaluate(bundle, repo_graph)
    assert "__init__.py" not in report.hallucinated_file


def test_existing_relative_dot_path_is_not_hallucination():
    repo_graph = RepositoryIntelligenceGraph(
        files=[FileNode(path="scripts/docs.py", name="docs.py", file_type=FileType.SOURCE)]
    )
    bundle = AnswerBundle(
        conclusion="入口来源提到了 ./scripts/docs.py。",
        evidence=[evidence(SourceType.CODE, "scripts/docs.py")],
        answer_type="entrypoints",
    )
    report = Evaluator().evaluate(bundle, repo_graph)
    assert "./scripts/docs.py" not in report.hallucinated_file


def test_package_json_is_not_split_into_package_js():
    repo_graph = RepositoryIntelligenceGraph(
        files=[FileNode(path="package.json", name="package.json", file_type=FileType.CONFIG)]
    )
    bundle = AnswerBundle(
        conclusion="请查看 package.json。",
        evidence=[evidence(SourceType.CONFIG, "package.json")],
        answer_type="setup_run",
    )
    report = Evaluator().evaluate(bundle, repo_graph)
    assert "package.js" not in report.hallucinated_file


def test_fabricated_command_is_hallucination():
    bundle = AnswerBundle(
        conclusion="请运行 python scripts/missing.py。",
        evidence=[evidence()],
        steps=["运行 python scripts/missing.py"],
    )
    report = Evaluator().evaluate(bundle, graph())
    assert report.passed is False
    assert "python scripts/missing.py" in report.hallucinated_command

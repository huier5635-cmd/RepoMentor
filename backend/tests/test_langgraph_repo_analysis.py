from __future__ import annotations

from pathlib import Path

from app.core.orchestrator import Orchestrator
from app.graphs.repo_analysis_graph import RepoAnalysisGraph


def write_tiny_repo(root: Path) -> Path:
    (root / "src").mkdir()
    (root / "scripts").mkdir()
    (root / "tests").mkdir()
    (root / "README.md").write_text(
        "\n".join(
            [
                "# Tiny Repo",
                "```bash",
                "pip install -r requirements.txt",
                "python scripts/run_demo.py",
                "python -m pytest tests",
                "```",
            ]
        ),
        encoding="utf-8",
    )
    (root / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    (root / "src" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "demo_app.py").write_text(
        "def add(a, b):\n    return a + b\n",
        encoding="utf-8",
    )
    (root / "scripts" / "run_demo.py").write_text(
        "from src.demo_app import add\n\nprint(add(1, 2))\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_demo_app.py").write_text(
        "from src.demo_app import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n",
        encoding="utf-8",
    )
    return root


def test_repo_analysis_graph_runs_existing_workers(tmp_path):
    repo = write_tiny_repo(tmp_path)
    graph = RepoAnalysisGraph(Orchestrator())

    response, state = graph.invoke(str(repo))

    assert response.status == "done"
    assert response.repo_id
    assert response.files
    assert response.worker_outputs
    assert response.entrypoints
    assert state["status"] == "completed"
    assert state["thread_id"] == f"analyze:{response.repo_id}"
    assert any(item["event_type"] == "checkpoint" for item in state["graph_trace"])

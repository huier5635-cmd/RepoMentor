from __future__ import annotations

from app.core.orchestrator import Orchestrator
from app.graphs.qa_graph import QAGraph
from test_langgraph_repo_analysis import write_tiny_repo


def test_qa_graph_returns_final_answer_with_self_check(tmp_path):
    repo = write_tiny_repo(tmp_path)
    legacy = Orchestrator()
    analysis = legacy.analyze_repo(str(repo))
    graph = QAGraph(legacy)

    final, state = graph.invoke(analysis.repo_id, "how to run this project setup install")

    assert final.conclusion
    assert final.self_check
    assert final.model_info.provider
    assert state["final_answer"]
    assert state["thread_id"].startswith(f"qa:{analysis.repo_id}:")

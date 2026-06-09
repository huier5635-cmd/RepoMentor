from __future__ import annotations

from app.core.schemas import EvidenceItem, SourceType, WorkerOutput, WorkerStatus
from app.graphs.state import create_initial_state, merge_worker_output_into_state, state_to_shared_memory


def test_langgraph_state_merges_worker_evidence_once():
    state = create_initial_state(thread_id="analyze:r1", repo_id="r1")
    evidence = EvidenceItem(
        evidence_id="ev1",
        source_type=SourceType.DOCS,
        source_ref="README.md",
        quote="python scripts/run_demo.py",
        supports_claim="demo command",
    )
    output = WorkerOutput(
        worker_name="Docs Worker",
        task="docs",
        status=WorkerStatus.SUCCESS,
        findings=["found docs"],
        evidence=[evidence],
    )

    merge_worker_output_into_state(state, output)
    merge_worker_output_into_state(state, output)

    assert len(state["worker_outputs"]) == 1
    assert len(state["retrieved_evidence"]) == 1
    assert state["completed_workers"] == ["Docs Worker"]


def test_langgraph_state_exports_shared_memory():
    state = create_initial_state(thread_id="qa:r1:s1", repo_id="r1", user_question="how to run")
    state["retrieved_evidence"] = [
        EvidenceItem(
            evidence_id="ev1",
            source_type=SourceType.COMMAND,
            source_ref="README.md",
            quote="python -m pytest tests",
            supports_claim="test command",
        ).model_dump(mode="json")
    ]

    memory = state_to_shared_memory(state)

    assert memory.session_id == state["session_id"]
    assert memory.user_question == "how to run"
    assert len(memory.retrieved_evidence) == 1

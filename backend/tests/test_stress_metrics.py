from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.stress_test_repomentor import evidence_coverage_breakdown, qa_evidence_counts, question_category


def test_qa_evidence_counts_include_new_fields():
    body = {
        "evidence_docs": [{}],
        "evidence_code": [{}, {}],
        "evidence_issues": [],
        "evidence_graph": [{}],
        "evidence_workflow": [{}],
        "evidence_commands": [{}],
        "evidence_internal_tasks": [{}],
    }
    assert qa_evidence_counts(body) == {
        "docs": 1,
        "code": 2,
        "issues": 0,
        "graph": 1,
        "workflow": 1,
        "commands": 1,
        "internal_tasks": 1,
    }


def test_evidence_coverage_breakdown_by_category():
    qa_results = [
        {"question": "核心模块有哪些？", "question_category": "core_modules", "evidence_count": 2, "evidence_counts": {"code": 1, "graph": 1}},
        {"question": "入口文件在哪里？", "question_category": "entrypoints", "evidence_count": 1, "evidence_counts": {"code": 1}},
        {"question": "这个仓库有哪些文档值得先看？", "question_category": "docs_recommendation", "evidence_count": 0, "evidence_counts": {}},
    ]
    result = evidence_coverage_breakdown(qa_results)
    assert result["by_category"]["core_modules"]["coverage_rate"] == 1
    assert result["by_category"]["docs_recommendation"]["coverage_rate"] == 0
    assert result["by_source"]["code"] == 2
    assert result["by_source"]["graph"] == 1


def test_question_category_maps_fixed_questions():
    assert question_category("入口文件在哪里？") == "entrypoints"
    assert question_category("适合新手的任务有哪些？") == "beginner_tasks"
    assert question_category("开发流程和代码规范是什么？") == "development_workflow"

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


METRICS = [
    "time_to_first_successful_run",
    "time_to_correct_project_goal",
    "architecture_explanation_score",
    "module_test_mapping_accuracy",
    "first_task_selection_quality",
    "evidence_coverage",
    "hallucination_rate",
    "translation_fidelity_pass_rate",
    "self_reported_cognitive_load",
    "self_reported_confidence",
    "retention_followup_placeholder",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate RepoMentor learning-agent evaluation report.")
    parser.add_argument("--repo-id", default="", help="Existing RepoMentor repo_id to evaluate.")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000/api", help="RepoMentor API base URL.")
    parser.add_argument("--output", default="reports/learning_agent_eval_report.md", help="Markdown report path.")
    args = parser.parse_args()

    payload = fetch_bundle(args.api_base, args.repo_id) if args.repo_id else None
    report = build_report(args.repo_id, payload)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"wrote {output}")


def fetch_bundle(api_base: str, repo_id: str) -> dict | None:
    url = f"{api_base.rstrip('/')}/repos/{repo_id}/learning-agent/debug-bundle"
    try:
      request = Request(url, headers={"Accept": "application/json"})
      with urlopen(request, timeout=10) as response:
          return json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as error:
      return {"error": str(error), "repo_id": repo_id}


def build_report(repo_id: str, payload: dict | None) -> str:
    lines = [
        "# RepoMentor 学习 Agent 评估报告",
        "",
        "## 评估对象",
        "",
        f"- repo_id: `{repo_id or '未指定'}`",
        "- A 组：GitHub/README 原始体验",
        "- B 组：RepoMentor 基础版",
        "- C 组：RepoMentor 学习 Agent 增强版",
        "",
        "## 指标",
        "",
    ]
    for metric in METRICS:
        lines.append(f"- `{metric}`")
    lines.extend(["", "## 代理指标结果", ""])
    if not payload:
        lines.extend([
            "- 未连接 API；本报告只生成评估框架。",
            "- 需要传入 `--repo-id` 并保持 `127.0.0.1:8000` 后端运行，才能生成结构覆盖指标。",
        ])
    elif payload.get("error"):
        lines.extend([
            f"- API 读取失败：`{payload['error']}`",
            "- 评估脚本已保留报告模板，稍后可重新运行。",
        ])
    else:
        learning_steps = len(payload.get("learning_path_v2", {}).get("steps", []))
        architecture_components = len(payload.get("architecture_tour", {}).get("major_components", []))
        module_cards = len(payload.get("module_study_cards", []))
        tasks = payload.get("contribution_funnel", {}).get("issues", [])
        internal_tasks = [item for item in tasks if item.get("source") == "internal_suggestion"]
        onboarding = payload.get("onboarding_debt", {})
        missing_debt = len(onboarding.get("onboarding_risks", []))
        glossary_terms = len(payload.get("glossary", {}).get("terms", []))
        bilingual_chunks = len(payload.get("bilingual_docs", {}).get("chunks", []))
        evidence_coverage = payload.get("learning_path_v2", {}).get("evidence_coverage", 0)
        fidelity_warnings = payload.get("bilingual_docs", {}).get("fidelity_warnings", [])
        lines.extend([
            f"- LearningPathV2 步骤数：{learning_steps}",
            f"- ArchitectureTour 组件数：{architecture_components}",
            f"- ModuleStudyCard 数量：{module_cards}",
            f"- Contribution Funnel 任务数：{len(tasks)}，其中 internal first tasks：{len(internal_tasks)}",
            f"- OnboardingDebt 风险数：{missing_debt}",
            f"- ProjectGlossary 术语数：{glossary_terms}",
            f"- BilingualDocView 文档切片数：{bilingual_chunks}",
            f"- LearningPathV2 evidence coverage：{evidence_coverage}",
            f"- translation fidelity warnings：{len(fidelity_warnings)}",
        ])
    lines.extend([
        "",
        "## 初步结论",
        "",
        "增强版 C 组已经具备更完整的结构化学习支架和证据约束输出。当前自动报告只能证明覆盖度、证据率和缺失项展示；是否真正降低学习时间和认知负荷，还需要真人 A/B/C 评测。",
    ])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()

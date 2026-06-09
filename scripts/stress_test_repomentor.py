from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import platform
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


QUESTIONS = [
    "这个仓库是干什么的？",
    "这个项目怎么启动？",
    "怎么安装依赖？",
    "怎么运行测试？",
    "核心模块有哪些？",
    "我应该按什么顺序学习？",
    "开发流程和代码规范是什么？",
    "修改一个核心文件后应该跑哪些测试？",
    "适合新手的任务有哪些？",
    "这个项目有没有 CI / lint / format？",
    "入口文件在哪里？",
    "这个仓库有哪些文档值得先看？",
]

SETUP_QUESTION = "这个项目怎么启动？"
SECRET_RE = re.compile(r"sk-[A-Za-z0-9_\-]{8,}")
PATH_RE = re.compile(r"(?<!https://)(?<!http://)(?<![\w:/.-])([\w./\\-]+\.(?:py|js|jsx|ts|tsx|md|json|toml|yml|yaml|txt|css|html|ini|cfg))(?![\w.-])")
ISSUE_RE = re.compile(r"#(\d+)")
EVIDENCE_FIELDS = {
    "docs": "evidence_docs",
    "code": "evidence_code",
    "issues": "evidence_issues",
    "graph": "evidence_graph",
    "workflow": "evidence_workflow",
    "commands": "evidence_commands",
    "internal_tasks": "evidence_internal_tasks",
}


class ApiClient:
    def __init__(self, base_url: str, timeout: int = 90) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get(self, path: str, timeout: int | None = None) -> tuple[int, Any, float]:
        return self._request("GET", path, None, timeout)

    def post(self, path: str, payload: dict[str, Any], timeout: int | None = None) -> tuple[int, Any, float]:
        return self._request("POST", path, payload, timeout)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None, timeout: int | None) -> tuple[int, Any, float]:
        url = f"{self.base_url}{path}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"}
        req = request.Request(url, data=body, headers=headers, method=method)
        started = time.perf_counter()
        try:
            with request.urlopen(req, timeout=timeout or self.timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
                elapsed = time.perf_counter() - started
                return response.status, json.loads(raw) if raw else {}, elapsed
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            elapsed = time.perf_counter() - started
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {"detail": raw}
            return exc.code, parsed, elapsed
        except Exception as exc:
            elapsed = time.perf_counter() - started
            return 0, {"detail": str(exc)}, elapsed


def main() -> int:
    parser = argparse.ArgumentParser(description="RepoMentor stress and stability acceptance test")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--provider", choices=["mock", "deepseek"], default="mock")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--output-dir", default="reports")
    parser.add_argument("--skip-large", action="store_true")
    parser.add_argument("--repo-list", default="tests/fixtures/stress_repos.json")
    parser.add_argument("--orchestrator", choices=["legacy", "langgraph"], default="legacy")
    args = parser.parse_args()

    root = Path.cwd()
    output_dir = root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    client = ApiClient(args.base_url)

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "base_url": args.base_url,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "provider_requested_by_test": args.provider,
            "orchestrator_requested_by_test": args.orchestrator,
            "concurrency": args.concurrency,
            "skip_large": args.skip_large,
        },
        "preflight": {},
        "repositories": [],
        "invalid_repositories": [],
        "qa_concurrency": {},
        "frontend_checks": {},
        "summary": {},
        "pass_fail": {},
        "known_bugs": [],
        "fixed_bugs": [],
        "known_limitations": [],
        "upgrade_recommendations": {},
    }

    preflight(client, args.provider, args.orchestrator, report)
    repos = load_repos(root / args.repo_list, args.skip_large)

    success_records: list[dict[str, Any]] = []
    for item in repos:
        record = test_repository(client, item, args.provider)
        if item.get("expected") == "error":
            report["invalid_repositories"].append(record)
        else:
            report["repositories"].append(record)
            if record.get("analyze_status") == "success":
                success_records.append(record)

    concurrency_result = run_concurrent_qa(client, success_records, args.concurrency, args.provider)
    report["qa_concurrency"] = concurrency_result
    report["frontend_checks"] = frontend_static_checks(root)
    finalize_summary(report)
    write_reports(root, output_dir, report)
    return 0 if report["pass_fail"].get("overall") == "pass" else 1


def preflight(client: ApiClient, provider: str, orchestrator: str, report: dict[str, Any]) -> None:
    health_status, health_body, health_elapsed = client.get("/api/health", timeout=15)
    report["preflight"]["health"] = {"status_code": health_status, "body": health_body, "elapsed_seconds": health_elapsed}
    graph_status_code, graph_status_body, graph_status_elapsed = client.get("/api/graph/status", timeout=15)
    report["preflight"]["graph_status"] = {
        "status_code": graph_status_code,
        "body": sanitize(graph_status_body),
        "elapsed_seconds": graph_status_elapsed,
    }
    active_orchestrator = graph_status_body.get("active_orchestrator") if isinstance(graph_status_body, dict) else ""
    if active_orchestrator and active_orchestrator != orchestrator:
        report.setdefault("warnings", []).append(
            f"orchestrator requested by test is {orchestrator}, but backend reports {active_orchestrator}; restart backend with LANGGRAPH_ENABLED to switch."
        )
    status_code, status_body, status_elapsed = client.get("/api/model/status", timeout=15)
    report["preflight"]["model_status_before"] = sanitize(status_body)
    report["preflight"]["model_status_code"] = status_code
    report["preflight"]["model_status_elapsed_seconds"] = status_elapsed
    if provider == "mock":
        cfg_status, cfg_body, _ = client.post("/api/model/config", {"provider": "mock", "persist": False}, timeout=20)
        report["preflight"]["model_config"] = {"status_code": cfg_status, "body": sanitize(cfg_body)}
        report["preflight"]["model_mode_note"] = "no-real-llm baseline"
    else:
        cfg_status, cfg_body, _ = client.post(
            "/api/model/config",
            {"provider": "deepseek", "model": "deepseek-chat", "base_url": "https://api.deepseek.com", "api_key": "", "persist": False},
            timeout=20,
        )
        report["preflight"]["model_config"] = {"status_code": cfg_status, "body": sanitize(cfg_body)}
        if cfg_body.get("fallback_to_mock"):
            report.setdefault("warnings", []).append("DeepSeek requested but fallback_to_mock=true; likely missing DeepSeek API Key.")
    test_status, test_body, test_elapsed = client.post("/api/model/test", {}, timeout=30)
    report["preflight"]["model_test"] = {"status_code": test_status, "body": sanitize(test_body), "elapsed_seconds": test_elapsed}


def load_repos(path: Path, skip_large: bool) -> list[dict[str, Any]]:
    repos = json.loads(path.read_text(encoding="utf-8"))
    if skip_large:
        return [item for item in repos if not item.get("large")]
    return repos


def test_repository(client: ApiClient, item: dict[str, Any], provider: str) -> dict[str, Any]:
    record: dict[str, Any] = {
        "name": item.get("name", ""),
        "repo_url": item.get("repo_url", ""),
        "category": item.get("category", ""),
        "expected": item.get("expected", "success"),
        "warnings": [],
        "errors": [],
    }
    repo_url = item.get("repo_url", "")
    status, body, elapsed = client.post("/api/repos/analyze", {"repo_url": repo_url}, timeout=260)
    record["analyze_status_code"] = status
    record["elapsed_seconds"] = round(elapsed, 3)
    if item.get("expected") == "error":
        record["analyze_status"] = "expected_error" if status >= 400 or status == 0 else "unexpected_success"
        record["errors"] = [] if record["analyze_status"] == "expected_error" else ["Invalid repository unexpectedly analyzed successfully."]
        record["error_detail"] = readable_error(body)
        return record

    if status >= 400 or status == 0:
        record["analyze_status"] = "failed"
        record["errors"].append(readable_error(body))
        return record

    record["analyze_status"] = "success"
    analysis = body
    repo_id = analysis.get("repo_id", "")
    record["repo_id"] = repo_id
    record["analysis_session_id"] = analysis.get("session_id", "")
    collect_analyze_metrics(record, analysis)

    graph_status, graph, _ = client.get(f"/api/repos/{repo_id}/graph", timeout=120)
    data_status, data_layer, _ = client.get(f"/api/debug/repos/{repo_id}/data-layer", timeout=120)
    repo_graph_status, repository_graph, _ = client.get(f"/api/debug/repos/{repo_id}/repository-graph", timeout=120)
    record["graph_status_code"] = graph_status
    record["data_layer_status_code"] = data_status
    record["repository_graph_status_code"] = repo_graph_status
    if graph_status < 400:
        collect_graph_metrics(record, graph)
    if data_status < 400 and repo_graph_status < 400:
        record["docs_chunks_count"] = data_layer.get("chunks_count", 0)
        record["data_layer_checks"] = compare_data_layer(data_layer, repository_graph)
        if record["data_layer_checks"]["mismatches"]:
            record["warnings"].extend([f"data_layer_mismatch: {item}" for item in record["data_layer_checks"]["mismatches"]])

    record["learning_path"] = test_learning_path(client, repo_id)
    record["development_workflow"] = test_development_workflow(client, repo_id)
    record["issue_recommendations"] = test_issue_recommendations(client, repo_id, record)
    record["qa_results"] = test_fixed_qa(client, repo_id, record, provider, graph if graph_status < 400 else {})
    record["debug_console_checks"] = test_debug_console(client, repo_id, record.get("analysis_session_id", ""))
    apply_repository_pass_fail(record)
    return record


def collect_analyze_metrics(record: dict[str, Any], analysis: dict[str, Any]) -> None:
    files = analysis.get("files", [])
    workers = analysis.get("worker_outputs", [])
    record.update(
        {
            "files_count": len(files),
            "docs_files_count": count_files(files, {"docs", "docs_legal", "docs_reference", "docs_static"}),
            "test_files_count": count_files(files, {"test"}),
            "quality_commands_count": len(analysis.get("quality_commands", [])),
            "setup_commands_count": len(analysis.get("setup_commands", [])),
            "run_commands_count": len(analysis.get("run_commands", [])),
            "test_commands_count": len(analysis.get("test_commands", [])),
            "build_commands_count": len(analysis.get("build_commands", [])),
            "lint_commands_count": len(analysis.get("lint_commands", [])),
            "format_commands_count": len(analysis.get("format_commands", [])),
            "open_issues_count": analysis.get("issues_count", 0),
            "worker_success_count": sum(1 for item in workers if item.get("status") == "success"),
            "worker_partial_count": sum(1 for item in workers if item.get("status") == "partial"),
            "worker_failed_count": sum(1 for item in workers if item.get("status") == "failed"),
        }
    )
    if record["files_count"] <= 0:
        record["errors"].append("Normal repository has files_count=0.")
    if analysis.get("readme_exists") and record["docs_files_count"] <= 0:
        record["warnings"].append("README exists but docs_files_count=0.")


DOC_EDGE_TYPES = {"documents", "mentions"}


def edge_type(edge: dict[str, Any]) -> str:
    return str(edge.get("edge_type") or edge.get("type") or edge.get("relation") or "")


def extract_edges(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("edges",):
        edges = payload.get(key)
        if isinstance(edges, list) and edges:
            return edges
    for key in ("raw_graph", "graph"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            edges = nested.get("edges")
            if isinstance(edges, list) and edges:
                return edges
    return []


def extract_doc_edges(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [edge for edge in extract_edges(payload) if edge_type(edge) in DOC_EDGE_TYPES]


def collect_graph_metrics(record: dict[str, Any], graph: dict[str, Any]) -> None:
    files = graph.get("files", [])
    tests = graph.get("tests", [])
    docs_edges = extract_doc_edges(graph)
    record.update(
        {
            "symbols_count": len(graph.get("symbols", [])),
            "imports_count": len(graph.get("imports", [])),
            "unresolved_imports_count": len(graph.get("unresolved_imports", [])),
            "docs_edges_count": len(docs_edges),
            "test_edges_count": len(tests),
            "quality_commands_count": len(graph.get("quality_commands", [])),
            "setup_commands_count": len(graph.get("commands", {}).get("setup", [])),
            "run_commands_count": len(graph.get("commands", {}).get("run", [])),
            "test_commands_count": len(graph.get("commands", {}).get("test", [])),
            "build_commands_count": len(graph.get("commands", {}).get("build", [])),
            "lint_commands_count": len(graph.get("commands", {}).get("lint", [])),
            "format_commands_count": len(graph.get("commands", {}).get("format", [])),
        }
    )
    if looks_like_code_repo(files) and record["symbols_count"] <= 0:
        record["warnings"].append("Code repository has symbols_count=0.")
    if record.get("test_files_count", 0) > 0 and record["test_edges_count"] <= 0:
        record["warnings"].append("Test files found but test_edges_count=0.")


def compare_data_layer(data_layer: dict[str, Any], repository_graph: dict[str, Any]) -> dict[str, Any]:
    summary = data_layer.get("graph_summary", {}) or {}
    details = {
        "symbols": len(data_layer.get("symbols") or repository_graph.get("symbols", [])),
        "imports": len(data_layer.get("imports") or repository_graph.get("imports", [])),
        "tests": len(data_layer.get("tests") or repository_graph.get("tests", [])),
        "docs": len(extract_doc_edges(data_layer)) or len(extract_doc_edges(repository_graph)),
        "quality_commands": len(data_layer.get("quality_commands") or repository_graph.get("quality_commands", [])),
    }
    mismatches: list[str] = []
    for key, value in details.items():
        summary_value = summary.get(key, 0)
        if value > 0 and summary_value == 0:
            mismatches.append(f"{key} summary=0 detail={value}")
    workflow = summary.get("development_workflow") or data_layer.get("development_workflow")
    if isinstance(workflow, dict):
        workflow_state = workflow.get("status") or "ready"
    else:
        workflow_state = workflow or "missing"
    if workflow_state not in {"ready", "partial", "missing"}:
        mismatches.append(f"development_workflow invalid state={workflow_state}")
    return {"summary": summary, "details": details, "mismatches": mismatches, "development_workflow_state": workflow_state}


def test_learning_path(client: ApiClient, repo_id: str) -> dict[str, Any]:
    status, body, elapsed = client.get(f"/api/repos/{repo_id}/learning-path", timeout=120)
    result = {"status_code": status, "elapsed_seconds": round(elapsed, 3), "errors": [], "warnings": []}
    if status >= 400 or status == 0:
        result["errors"].append(readable_error(body))
        return result
    steps = body.get("steps", [])
    titles = " ".join(step.get("title", "") + " " + step.get("reason", "") for step in steps)
    result["steps_count"] = len(steps)
    result["evidence_steps_count"] = sum(1 for step in steps if step.get("evidence"))
    required = ["README", "启动", "核心", "测试", "开发", "任务"]
    result["required_coverage"] = {key: key.lower() in titles.lower() for key in required}
    if len(steps) < 5:
        result["errors"].append("Learning path has fewer than 5 steps.")
    if result["evidence_steps_count"] == 0:
        result["warnings"].append("Learning path steps have no evidence.")
    if sum(result["required_coverage"].values()) < 4:
        result["warnings"].append("Learning path misses several required themes.")
    result["self_check"] = body.get("self_check", {})
    return result


def test_development_workflow(client: ApiClient, repo_id: str) -> dict[str, Any]:
    status, body, elapsed = client.get(f"/api/repos/{repo_id}/development-workflow", timeout=120)
    result = {"status_code": status, "elapsed_seconds": round(elapsed, 3), "errors": [], "warnings": []}
    if status >= 400 or status == 0:
        result["errors"].append(readable_error(body))
        return result
    for key in [
        "quality_commands",
        "setup_steps",
        "development_commands",
        "test_commands",
        "lint_commands",
        "format_commands",
        "type_check_commands",
        "build_commands",
        "contribution_rules",
        "pull_request_rules",
        "ci_rules",
        "code_style_rules",
        "uncertainties",
    ]:
        value = body.get(key, [])
        result[f"{key}_count"] = len(value) if isinstance(value, list) else 0
    if result["setup_steps_count"] == 0 and result["quality_commands_count"] == 0:
        result["warnings"].append("No setup steps or quality commands detected.")
    if result["test_commands_count"] == 0:
        result["warnings"].append("No test commands detected; should be uncertainty if evidence is missing.")
    result["self_check"] = body.get("self_check", {})
    return result


def test_issue_recommendations(client: ApiClient, repo_id: str, repo_record: dict[str, Any]) -> dict[str, Any]:
    status, body, elapsed = client.get(f"/api/repos/{repo_id}/issues/recommend", timeout=120)
    result = {"status_code": status, "elapsed_seconds": round(elapsed, 3), "errors": [], "warnings": []}
    if status >= 400 or status == 0:
        result["errors"].append(readable_error(body))
        return result
    issues = body.get("issues", [])
    result["items_count"] = len(issues)
    result["internal_tasks_count"] = sum(1 for item in issues if item.get("source") == "internal_suggestion" or item.get("is_github_issue") is False)
    result["github_issues_count"] = sum(1 for item in issues if item.get("is_github_issue") is True)
    result["self_check"] = body.get("self_check", {})
    if repo_record.get("open_issues_count", 0) == 0 and result["internal_tasks_count"] == 0:
        result["errors"].append("No open issues and no internal first tasks generated.")
    if not issues:
        result["warnings"].append("Issue recommendation list is empty.")
    return result


def test_fixed_qa(client: ApiClient, repo_id: str, repo_record: dict[str, Any], provider: str, graph: dict[str, Any]) -> list[dict[str, Any]]:
    commands = graph_commands(graph)
    files = {item.get("path", "").replace("\\", "/") for item in graph.get("files", [])}
    issue_numbers = {str(item.get("issue_number")) for item in graph.get("snapshot", {}).get("issues", []) if item.get("issue_number") is not None}
    results = []
    for question in QUESTIONS:
        results.append(run_qa_check(client, repo_id, question, provider, commands, files, issue_numbers, repo_record))
    return results


def qa_evidence_counts(body: dict[str, Any]) -> dict[str, int]:
    return {name: len(body.get(field, []) or []) for name, field in EVIDENCE_FIELDS.items()}


def question_category(question: str) -> str:
    lowered = question.lower()
    if question == SETUP_QUESTION or any(token in lowered for token in ["怎么启动", "安装依赖", "运行测试"]):
        return "setup_run"
    if "核心模块" in question:
        return "core_modules"
    if "入口" in question:
        return "entrypoints"
    if "文档" in question:
        return "docs_recommendation"
    if "顺序学习" in question or "学习" in question:
        return "learning_path"
    if "新手" in question or "任务" in question:
        return "beginner_tasks"
    if "开发流程" in question or "代码规范" in question or "ci" in lowered or "lint" in lowered or "format" in lowered:
        return "development_workflow"
    if "干什么" in question or "做什么" in question:
        return "overview"
    return "general"


def evidence_coverage_breakdown(qa_results: list[dict[str, Any]]) -> dict[str, Any]:
    by_category: dict[str, dict[str, Any]] = {}
    by_source = {name: 0 for name in EVIDENCE_FIELDS}
    for qa in qa_results:
        category = qa.get("question_category") or question_category(qa.get("question", ""))
        bucket = by_category.setdefault(
            category,
            {
                "total": 0,
                "covered": 0,
                "docs": 0,
                "code": 0,
                "issues": 0,
                "graph": 0,
                "workflow": 0,
                "commands": 0,
                "internal_tasks": 0,
            },
        )
        bucket["total"] += 1
        counts = qa.get("evidence_counts", {}) or {}
        if qa.get("evidence_count", 0) > 0:
            bucket["covered"] += 1
        for name in EVIDENCE_FIELDS:
            count = int(counts.get(name, 0) or 0)
            bucket[name] += count
            by_source[name] += count
    for bucket in by_category.values():
        bucket["coverage_rate"] = round(bucket["covered"] / bucket["total"], 4) if bucket["total"] else 0
    return {"by_category": by_category, "by_source": by_source}


def run_qa_check(
    client: ApiClient,
    repo_id: str,
    question: str,
    provider: str,
    commands: set[str],
    files: set[str],
    issue_numbers: set[str],
    repo_record: dict[str, Any],
) -> dict[str, Any]:
    status, body, elapsed = client.post(f"/api/repos/{repo_id}/qa", {"question": question}, timeout=120)
    result = {"question": question, "status_code": status, "elapsed_seconds": round(elapsed, 3), "errors": [], "warnings": []}
    if status >= 400 or status == 0:
        result["errors"].append(readable_error(body))
        return result
    evidence_counts = qa_evidence_counts(body)
    evidence_count = sum(evidence_counts.values())
    self_check = body.get("self_check", {})
    result.update(
        {
            "has_conclusion": bool(body.get("conclusion")),
            "question_category": question_category(question),
            "evidence_count": evidence_count,
            "evidence_counts": evidence_counts,
            "self_check": self_check,
            "self_check_passed": self_check.get("passed"),
            "missing_evidence_count": len(self_check.get("missing_evidence", [])),
            "hallucination_risk_count": len(self_check.get("hallucination_risks", [])),
            "verifiable_commands": body.get("verifiable_commands", []),
            "model_info": sanitize(body.get("model_info", {})),
        }
    )
    if not result["has_conclusion"]:
        result["errors"].append("QA response missing conclusion.")
    if evidence_count == 0 and "证据不足" not in str(body.get("conclusion", "")):
        result["errors"].append("QA response has no evidence and does not explicitly say evidence is insufficient.")
    if not self_check:
        result["errors"].append("QA response missing self_check.")
    if self_check.get("passed") is True and self_check.get("missing_evidence"):
        result["errors"].append("self_check passed but missing_evidence is not empty.")
    if any(token in question for token in ["启动", "安装", "测试"]) and not body.get("verifiable_commands"):
        result["errors"].append("Setup/install/test question missing verifiable_commands.")
    command_hallucinations = [cmd for cmd in body.get("verifiable_commands", []) if normalize_command(cmd) not in commands]
    result["command_hallucinations"] = command_hallucinations
    if command_hallucinations:
        result["errors"].append(f"Commands not found in evidence/graph commands: {command_hallucinations}")
    narrative_text = " ".join([str(body.get("conclusion", "")), " ".join(body.get("steps", [])), " ".join(body.get("risks", []))])
    command_text = " ".join(body.get("verifiable_commands", []))
    text = f"{narrative_text} {command_text}"
    missing_paths = sorted(
        {
            path.replace("\\", "/")
            for path in PATH_RE.findall(narrative_text)
            if not file_path_known(path, files)
            and not path.startswith("http")
            and not path_is_explicitly_missing(path, narrative_text)
            and path not in command_text
        }
    )
    result["missing_paths"] = missing_paths
    if missing_paths:
        result["errors"].append(f"Response referenced nonexistent file paths: {missing_paths[:5]}")
    missing_issues = sorted({num for num in ISSUE_RE.findall(text) if num not in issue_numbers})
    result["missing_issue_numbers"] = missing_issues
    if missing_issues and issue_numbers:
        result["errors"].append(f"Response referenced nonexistent issue numbers: {missing_issues[:5]}")
    if repo_record.get("open_issues_count", 0) == 0 and "任务" in question and "internal" not in json.dumps(body, ensure_ascii=False).lower() and "入门" not in text:
        result["warnings"].append("No open issues; QA task answer may not clearly expose internal first tasks.")
    if provider == "deepseek" and evidence_count > 0 and not body.get("model_info", {}).get("used_llm"):
        result["warnings"].append("DeepSeek mode requested but model_info.used_llm is not true.")
    if provider == "mock" and body.get("model_info", {}).get("used_llm"):
        result["errors"].append("Mock mode QA unexpectedly used real LLM.")
    if question == SETUP_QUESTION:
        check_setup_answer(result, body, repo_record)
    return result


def check_setup_answer(result: dict[str, Any], body: dict[str, Any], repo_record: dict[str, Any]) -> None:
    abstract_bad = "仓库启动/测试方式应以已解析到的文档、配置文件和构建脚本为准"
    text = " ".join([body.get("conclusion", ""), " ".join(body.get("steps", [])), " ".join(body.get("risks", [])), " ".join(body.get("verifiable_commands", []))])
    if abstract_bad in text:
        result["errors"].append("setup_run returned abstract conclusion instead of executable steps.")
    if not body.get("verifiable_commands"):
        result["errors"].append("setup_run missing verifiable commands.")
    if "resilience-copilot" in repo_record.get("repo_url", ""):
        required = ["pip install -r requirements.txt", "python scripts/run_demo.py", "python -m pytest tests"]
        missing = [cmd for cmd in required if normalize_command(cmd) not in {normalize_command(item) for item in body.get("verifiable_commands", [])}]
        if missing:
            result["errors"].append(f"resilience setup_run missing required commands: {missing}")
    normalized = [normalize_command(cmd) for cmd in body.get("verifiable_commands", [])]
    if len(normalized) != len(set(normalized)):
        result["errors"].append("setup_run verifiable_commands contain duplicates after slash normalization.")


def run_concurrent_qa(client: ApiClient, repos: list[dict[str, Any]], concurrency: int, provider: str) -> dict[str, Any]:
    jobs = []
    for repo in repos:
        repo_id = repo.get("repo_id")
        if not repo_id:
            continue
        for question in QUESTIONS:
            jobs.append((repo_id, repo.get("name", ""), question))
    latencies: list[float] = []
    failures: list[dict[str, Any]] = []
    successes = 0
    status_500 = 0
    timeouts = 0
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        future_map = {pool.submit(client.post, f"/api/repos/{repo_id}/qa", {"question": question}, 120): (repo_id, name, question) for repo_id, name, question in jobs}
        for future in concurrent.futures.as_completed(future_map):
            repo_id, name, question = future_map[future]
            status, body, elapsed = future.result()
            latencies.append(elapsed)
            if status == 200:
                successes += 1
                returned_repo = infer_repo_id_from_answer(body)
                if returned_repo and returned_repo != repo_id:
                    failures.append({"repo": name, "question": question, "reason": f"repo_id_mixed: {returned_repo} != {repo_id}"})
            else:
                failures.append({"repo": name, "question": question, "status_code": status, "error": readable_error(body)})
                if status == 500:
                    status_500 += 1
                if status == 0:
                    timeouts += 1
    return {
        "total_requests": len(jobs),
        "success_count": successes,
        "failure_count": len(jobs) - successes,
        "average_latency": round(statistics.mean(latencies), 3) if latencies else 0,
        "p95_latency": round(percentile(latencies, 95), 3) if latencies else 0,
        "max_latency": round(max(latencies), 3) if latencies else 0,
        "timeout_count": timeouts,
        "500_count": status_500,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "failures": failures[:20],
        "provider": provider,
    }


def test_debug_console(client: ApiClient, repo_id: str, session_id: str) -> dict[str, Any]:
    checks = {"errors": [], "warnings": []}
    endpoints = {
        "graph_status": "/api/graph/status",
        "agent_flow": f"/api/debug/repos/{repo_id}/agent-flow",
        "worker_outputs": f"/api/debug/repos/{repo_id}/worker-outputs",
        "data_layer": f"/api/debug/repos/{repo_id}/data-layer",
        "repository_graph": f"/api/debug/repos/{repo_id}/repository-graph",
        "analysis_graph_state": f"/api/debug/graph/analyze%3A{repo_id}/state",
        "analysis_graph_trace": f"/api/debug/graph/analyze%3A{repo_id}/trace",
    }
    if session_id:
        endpoints.update(
            {
                "shared_memory": f"/api/debug/session/{session_id}/memory",
                "retrieval_trace": f"/api/debug/session/{session_id}/retrieval-trace",
                "self_check": f"/api/debug/session/{session_id}/self-check",
                "final_answer_json": f"/api/debug/session/{session_id}/final-answer-json",
                "qa_graph_state": f"/api/debug/graph/qa%3A{repo_id}%3A{session_id}/state",
                "qa_graph_trace": f"/api/debug/graph/qa%3A{repo_id}%3A{session_id}/trace",
            }
        )
    for name, path in endpoints.items():
        status, body, elapsed = client.get(path, timeout=90)
        checks[name] = {"status_code": status, "elapsed_seconds": round(elapsed, 3)}
        if status >= 400 or status == 0:
            checks["warnings"].append(f"{name} unavailable: {readable_error(body)}")
    return checks


def frontend_static_checks(root: Path) -> dict[str, Any]:
    user = (root / "frontend/src/pages/UserDashboard.jsx").read_text(encoding="utf-8")
    debug = (root / "frontend/src/pages/DebugConsole.jsx").read_text(encoding="utf-8")
    model_debug = (root / "frontend/src/components/debug/ModelControlDebugPanel.jsx").read_text(encoding="utf-8")
    langgraph_debug = (root / "frontend/src/components/debug/LangGraphDebugPanel.jsx").read_text(encoding="utf-8")
    user_model = (root / "frontend/src/components/user/UserModelSwitch.jsx").read_text(encoding="utf-8")
    styles = (root / "frontend/src/styles.css").read_text(encoding="utf-8")
    return {
        "user_hides_agent_flow": "AgentFlowDebugPanel" not in user,
        "user_hides_worker_outputs": "WorkerOutputsDebugPanel" not in user,
        "user_hides_shared_memory": "SharedMemoryPanel" not in user,
        "user_model_has_no_password_input": 'type="password"' not in user_model,
        "debug_has_agent_flow": "AgentFlowDebugPanel" in debug,
        "debug_has_worker_outputs": "WorkerOutputsDebugPanel" in debug,
        "debug_has_shared_memory": "SharedMemoryPanel" in debug,
        "debug_has_retrieval_trace": "RetrievalTracePanel" in debug,
        "debug_has_final_json": "FinalAnswerJsonPanel" in debug,
        "debug_has_langgraph_panel": "LangGraphDebugPanel" in debug and "LangGraph 调试" in langgraph_debug,
        "debug_model_password_input": 'type="password"' in model_debug,
        "debug_trace_export": "TraceExportPanel" in debug,
        "model_control_full_row": "modelControlDebugPanel" in styles and "grid-column: 1 / -1" in styles,
        "raw_json_default_folded": "<details>" in model_debug,
        "api_key_not_in_frontend_defaults": not bool(SECRET_RE.search(user + debug + model_debug + langgraph_debug + user_model)),
    }


def finalize_summary(report: dict[str, Any]) -> None:
    repos = report["repositories"]
    successful = [repo for repo in repos if repo.get("analyze_status") == "success"]
    qa_results = [qa for repo in successful for qa in repo.get("qa_results", [])]
    total_qa = len(qa_results)
    qa_success = sum(1 for qa in qa_results if qa.get("status_code") == 200 and not qa.get("errors"))
    evidence_ok = sum(1 for qa in qa_results if qa.get("evidence_count", 0) > 0 or "证据不足" in str(qa))
    command_hallucinations = sum(len(qa.get("command_hallucinations", [])) for qa in qa_results)
    self_checks = [qa for qa in qa_results if qa.get("self_check")]
    self_check_passed = sum(1 for qa in self_checks if qa.get("self_check_passed") is True)
    internal_fallback_success = sum(1 for repo in successful if repo.get("open_issues_count", 0) == 0 and repo.get("issue_recommendations", {}).get("internal_tasks_count", 0) > 0)
    no_issue_repos = sum(1 for repo in successful if repo.get("open_issues_count", 0) == 0)
    analyze_times = [repo.get("elapsed_seconds", 0) for repo in successful]
    qa_times = [qa.get("elapsed_seconds", 0) for qa in qa_results if qa.get("status_code") == 200]
    report["summary"] = {
        "normal_repositories_tested": len(repos),
        "normal_repositories_analyze_success": len(successful),
        "invalid_repositories_tested": len(report["invalid_repositories"]),
        "invalid_repositories_expected_error": sum(1 for item in report["invalid_repositories"] if item.get("analyze_status") == "expected_error"),
        "average_analyze_time": round(statistics.mean(analyze_times), 3) if analyze_times else 0,
        "average_qa_time": round(statistics.mean(qa_times), 3) if qa_times else 0,
        "p95_qa_latency": round(percentile(qa_times, 95), 3) if qa_times else 0,
        "qa_success_rate": round(qa_success / total_qa, 4) if total_qa else 0,
        "evidence_coverage_rate": round(evidence_ok / total_qa, 4) if total_qa else 0,
        "command_hallucination_count": command_hallucinations,
        "self_check_pass_rate": round(self_check_passed / len(self_checks), 4) if self_checks else 0,
        "self_check_missing_rate": round(1 - (len(self_checks) / total_qa), 4) if total_qa else 0,
        "issue_fallback_success_count": internal_fallback_success,
        "no_issue_repos_count": no_issue_repos,
        "frontend_checks_passed": all(report["frontend_checks"].values()) if report.get("frontend_checks") else False,
        "api_key_leak_detected": bool(SECRET_RE.search(json.dumps(report, ensure_ascii=False))),
    }
    report["evidence_coverage_breakdown"] = evidence_coverage_breakdown(qa_results)
    summary = report["summary"]
    pass_fail = {
        "at_least_3_analyze_success": summary["normal_repositories_analyze_success"] >= 3,
        "normal_files_gt_zero": all(repo.get("files_count", 0) > 0 for repo in successful),
        "qa_success_rate_gte_90": summary["qa_success_rate"] >= 0.9,
        "evidence_coverage_gte_85": summary["evidence_coverage_rate"] >= 0.85,
        "command_hallucination_zero": summary["command_hallucination_count"] == 0,
        "self_check_missing_zero": summary["self_check_missing_rate"] == 0,
        "issue_fallback_success": summary["no_issue_repos_count"] == 0 or summary["issue_fallback_success_count"] == summary["no_issue_repos_count"],
        "frontend_user_no_raw_debug": report["frontend_checks"].get("user_hides_agent_flow") and report["frontend_checks"].get("user_hides_worker_outputs"),
        "debug_trace_available": report["frontend_checks"].get("debug_has_retrieval_trace") and report["frontend_checks"].get("debug_trace_export"),
        "debug_langgraph_panel_available": report["frontend_checks"].get("debug_has_langgraph_panel"),
        "no_api_key_leak": not summary["api_key_leak_detected"],
    }
    pass_fail["overall"] = "pass" if all(pass_fail.values()) else "fail"
    report["pass_fail"] = pass_fail
    report["known_limitations"] = derive_limitations(report)
    report["fixed_bugs"] = ["调试页模型控制和智能体流程调试布局重叠已修复", "模型控制用户/调试视图已拆分", "模型 API 状态返回不泄露 API Key"]
    report["known_bugs"] = derive_bugs(report)
    report["upgrade_recommendations"] = {
        "P0": [
            "修复压力测试发现的 bug",
            "强化 evidence 和 SelfCheck",
            "优化 setup_run 和 development workflow",
            "完善 internal first tasks",
        ],
        "P1": [
            "DeepSeek 深度接入 Code Explanation / LearningPath",
            "多仓库评测集",
            "README 和 Demo 视频",
            "评测报告",
        ],
        "P2": [
            "LangGraph 迁移",
            "checkpoint",
            "long-running repo analysis",
            "MCP server",
            "多用户任务队列",
        ],
    }


def derive_bugs(report: dict[str, Any]) -> list[str]:
    bugs: list[str] = []
    for repo in report["repositories"]:
        if repo.get("analyze_status") != "success":
            bugs.append(f"{repo.get('name')} analyze failed: {repo.get('errors')}")
        for warning in repo.get("warnings", []):
            if "data_layer_mismatch" in warning:
                bugs.append(f"{repo.get('name')} {warning}")
        for qa in repo.get("qa_results", []):
            for error_item in qa.get("errors", []):
                bugs.append(f"{repo.get('name')} QA[{qa.get('question')}]: {error_item}")
    return bugs[:50]


def derive_limitations(report: dict[str, Any]) -> list[str]:
    limitations = [
        "DeepSeek 真模型调用依赖本地运行时 API Key；无 Key 时按设计回退 Mock。",
        "压力测试不会并发 analyze 大仓库，只对已分析仓库做 QA 轻并发。",
        "前端大数据分页/折叠目前主要通过静态源代码和浏览器抽样验证，未覆盖所有超大仓库场景。",
    ]
    if report["summary"].get("command_hallucination_count", 0):
        limitations.append("部分 QA verifiable_commands 未能和 graph commands 完全对齐。")
    return limitations


def write_reports(root: Path, output_dir: Path, report: dict[str, Any]) -> None:
    sanitized = sanitize(report)
    (output_dir / "stress_report.json").write_text(json.dumps(sanitized, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "stress_report.md").write_text(markdown_report(sanitized), encoding="utf-8")
    (output_dir / "stress_summary.md").write_text(markdown_summary(sanitized), encoding="utf-8")
    (output_dir / "evidence_coverage_breakdown.md").write_text(markdown_evidence_breakdown(sanitized), encoding="utf-8")
    (output_dir / "langgraph_comparison_report.md").write_text(markdown_langgraph_comparison(sanitized), encoding="utf-8")
    (root / "docs/testing_plan.md").write_text(testing_plan_doc(), encoding="utf-8")
    (root / "docs/known_limitations.md").write_text(known_limitations_doc(sanitized), encoding="utf-8")
    (root / "docs/upgrade_recommendations.md").write_text(upgrade_recommendations_doc(sanitized), encoding="utf-8")


def markdown_langgraph_comparison(report: dict[str, Any]) -> str:
    graph_status = report.get("preflight", {}).get("graph_status", {}).get("body", {})
    summary = report.get("summary", {})
    pass_fail = report.get("pass_fail", {})
    repositories = report.get("repositories", [])
    lines = [
        "# LangGraph 迁移对比报告",
        "",
        f"- 生成时间：{report.get('generated_at', '')}",
        f"- 请求 Orchestrator：`{report.get('environment', {}).get('orchestrator_requested_by_test', 'legacy')}`",
        f"- 后端实际 Orchestrator：`{graph_status.get('active_orchestrator', 'unknown')}`",
        f"- LangGraph Enabled：`{graph_status.get('langgraph_enabled', False)}`",
        f"- Checkpoint：`{graph_status.get('checkpoint_backend', 'unknown')}` / `available={graph_status.get('checkpoint_available', False)}`",
        f"- Max Retries：`{graph_status.get('max_retries', '')}`",
        "",
        "## 验收指标",
        "",
        f"- analyze 成功：{summary.get('normal_repositories_analyze_success', 0)} / {summary.get('normal_repositories_tested', 0)}",
        f"- QA 成功率：{percent(summary.get('qa_success_rate', 0))}",
        f"- evidence 覆盖率：{percent(summary.get('evidence_coverage_rate', 0))}",
        f"- command hallucination：{summary.get('command_hallucination_count', 0)}",
        f"- SelfCheck 缺失率：{percent(summary.get('self_check_missing_rate', 0))}",
        f"- Issue fallback：{summary.get('issue_fallback_success_count', 0)} / {summary.get('no_issue_repos_count', 0)}",
        "",
        "## Debug API 抽样",
        "",
    ]
    for repo in repositories:
        checks = repo.get("debug_console_checks", {})
        lines.extend(
            [
                f"### {repo.get('name', repo.get('repo_id', 'repo'))}",
                f"- agent_flow：{checks.get('agent_flow', {}).get('status_code', 'n/a')}",
                f"- analysis_graph_state：{checks.get('analysis_graph_state', {}).get('status_code', 'n/a')}",
                f"- analysis_graph_trace：{checks.get('analysis_graph_trace', {}).get('status_code', 'n/a')}",
                f"- qa_graph_state：{checks.get('qa_graph_state', {}).get('status_code', 'n/a')}",
                f"- qa_graph_trace：{checks.get('qa_graph_trace', {}).get('status_code', 'n/a')}",
                "",
            ]
        )
    lines.extend(
        [
            "## Pass / Fail",
            "",
            *[f"- {key}: `{value}`" for key, value in pass_fail.items()],
            "",
        ]
    )
    return "\n".join(lines)


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# RepoMentor 压力测试报告",
        "",
        f"- 测试时间：{report['generated_at']}",
        f"- 测试环境：{report['environment']['platform']} / Python {report['environment']['python']}",
        f"- 模型模式：{report['environment']['provider_requested_by_test']}",
        f"- 整体结论：**{report['pass_fail']['overall'].upper()}**",
        "",
        "## 汇总指标",
        "",
        f"- 正常仓库 analyze 成功：{summary['normal_repositories_analyze_success']} / {summary['normal_repositories_tested']}",
        f"- 异常仓库可读错误：{summary['invalid_repositories_expected_error']} / {summary['invalid_repositories_tested']}",
        f"- 平均 analyze 时间：{summary['average_analyze_time']}s",
        f"- 平均 QA 时间：{summary['average_qa_time']}s",
        f"- p95 QA 延迟：{summary['p95_qa_latency']}s",
        f"- QA 成功率：{percent(summary['qa_success_rate'])}",
        f"- evidence 覆盖率：{percent(summary['evidence_coverage_rate'])}",
        f"- command hallucination 数量：{summary['command_hallucination_count']}",
        f"- SelfCheck 通过率：{percent(summary['self_check_pass_rate'])}",
        f"- SelfCheck 缺失率：{percent(summary['self_check_missing_rate'])}",
        f"- Issue fallback 成功：{summary['issue_fallback_success_count']} / {summary['no_issue_repos_count']}",
        f"- API Key 泄露：{'是' if summary['api_key_leak_detected'] else '否'}",
        "",
        "## 仓库列表与 Analyze 结果",
        "",
    ]
    for repo in report["repositories"]:
        lines.extend(
            [
                f"### {repo.get('name')}",
                f"- category：{repo.get('category', '')}",
                f"- URL：{repo.get('repo_url')}",
                f"- 状态：{repo.get('analyze_status')}",
                f"- repo_id：{repo.get('repo_id', '')}",
                f"- 用时：{repo.get('elapsed_seconds', 0)}s",
                f"- files/symbols/imports：{repo.get('files_count', 0)} / {repo.get('symbols_count', 0)} / {repo.get('imports_count', 0)}",
                f"- docs files/chunks/edges：{repo.get('docs_files_count', 0)} / {repo.get('docs_chunks_count', 0)} / {repo.get('docs_edges_count', 0)}",
                f"- tests files/edges：{repo.get('test_files_count', 0)} / {repo.get('test_edges_count', 0)}",
                f"- quality/run/test commands：{repo.get('quality_commands_count', 0)} / {repo.get('run_commands_count', 0)} / {repo.get('test_commands_count', 0)}",
                f"- open issues：{repo.get('open_issues_count', 0)}",
                f"- worker success/partial/failed：{repo.get('worker_success_count', 0)} / {repo.get('worker_partial_count', 0)} / {repo.get('worker_failed_count', 0)}",
                f"- warnings：{'; '.join(repo.get('warnings', [])) or '无'}",
                f"- errors：{'; '.join(repo.get('errors', [])) or '无'}",
                "",
            ]
        )
    lines.extend(["## 异常仓库", ""])
    for repo in report["invalid_repositories"]:
        lines.append(f"- {repo.get('name')}：{repo.get('analyze_status')}，{repo.get('error_detail')}")
    lines.extend(["", "## QA 结果", ""])
    for repo in report["repositories"]:
        if repo.get("analyze_status") != "success":
            continue
        qa_errors = sum(1 for qa in repo.get("qa_results", []) if qa.get("errors"))
        qa_warnings = sum(1 for qa in repo.get("qa_results", []) if qa.get("warnings"))
        lines.append(f"- {repo.get('name')}：QA {len(repo.get('qa_results', []))} 条，errors={qa_errors}，warnings={qa_warnings}")
    lines.extend(
        [
            "",
            "## 并发轻压测",
            "",
            f"- total_requests：{report['qa_concurrency'].get('total_requests', 0)}",
            f"- success_count：{report['qa_concurrency'].get('success_count', 0)}",
            f"- failure_count：{report['qa_concurrency'].get('failure_count', 0)}",
            f"- average_latency：{report['qa_concurrency'].get('average_latency', 0)}s",
            f"- p95_latency：{report['qa_concurrency'].get('p95_latency', 0)}s",
            f"- max_latency：{report['qa_concurrency'].get('max_latency', 0)}s",
            f"- timeout_count：{report['qa_concurrency'].get('timeout_count', 0)}",
            f"- 500_count：{report['qa_concurrency'].get('500_count', 0)}",
            "",
            "## 前端压力检查",
            "",
        ]
    )
    for key, value in report["frontend_checks"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## 已发现 bug", ""])
    lines.extend([f"- {item}" for item in report["known_bugs"]] or ["- 暂无"])
    lines.extend(["", "## 已修复 bug", ""])
    lines.extend([f"- {item}" for item in report["fixed_bugs"]] or ["- 暂无"])
    lines.extend(["", "## 仍存在的限制", ""])
    lines.extend([f"- {item}" for item in report["known_limitations"]])
    lines.extend(["", "## 下一阶段功能升级建议", ""])
    for priority, items in report["upgrade_recommendations"].items():
        lines.append(f"### {priority}")
        lines.extend([f"- {item}" for item in items])
    return "\n".join(lines) + "\n"


def markdown_summary(report: dict[str, Any]) -> str:
    summary = report["summary"]
    return "\n".join(
        [
            "# RepoMentor 压力测试摘要",
            "",
            f"- 整体结论：**{report['pass_fail']['overall'].upper()}**",
            f"- Analyze 成功仓库：{summary['normal_repositories_analyze_success']} / {summary['normal_repositories_tested']}",
            f"- QA 成功率：{percent(summary['qa_success_rate'])}",
            f"- evidence 覆盖率：{percent(summary['evidence_coverage_rate'])}",
            f"- command hallucination：{summary['command_hallucination_count']}",
            f"- SelfCheck 通过率：{percent(summary['self_check_pass_rate'])}",
            f"- 平均 analyze：{summary['average_analyze_time']}s",
            f"- 平均 QA：{summary['average_qa_time']}s",
            f"- p95 QA：{summary['p95_qa_latency']}s",
            f"- API Key 泄露：{'是' if summary['api_key_leak_detected'] else '否'}",
            "",
        ]
    )


def markdown_evidence_breakdown(report: dict[str, Any]) -> str:
    breakdown = report.get("evidence_coverage_breakdown", {})
    by_category = breakdown.get("by_category", {})
    by_source = breakdown.get("by_source", {})
    lines = [
        "# RepoMentor Evidence 覆盖率明细",
        "",
        "## 按 QA 类型",
        "",
        "| QA 类型 | 覆盖数 | 总数 | 覆盖率 | docs | code | issues | graph | workflow | commands | internal_tasks |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for category, item in sorted(by_category.items()):
        lines.append(
            f"| {category} | {item.get('covered', 0)} | {item.get('total', 0)} | {percent(item.get('coverage_rate', 0))} | "
            f"{item.get('docs', 0)} | {item.get('code', 0)} | {item.get('issues', 0)} | {item.get('graph', 0)} | "
            f"{item.get('workflow', 0)} | {item.get('commands', 0)} | {item.get('internal_tasks', 0)} |"
        )
    lines.extend(["", "## 按 Evidence 来源", ""])
    for source, count in sorted(by_source.items()):
        lines.append(f"- {source}: {count}")
    lines.append("")
    return "\n".join(lines)


def testing_plan_doc() -> str:
    return """# RepoMentor 测试计划

## 范围

- 公开 GitHub 仓库 analyze
- Repository Intelligence Graph 和 Data Layer 一致性
- Learning Path
- Development Workflow
- Issue Recommendation / internal first tasks
- 固定仓库级 QA
- Mock / DeepSeek 模型状态与 fallback
- Debug Console 与用户页展示隔离
- QA 轻并发

## 命令

```powershell
python scripts/stress_test_repomentor.py --base-url http://127.0.0.1:8000 --provider mock --concurrency 3 --output-dir reports --skip-large
```

## 通过标准

- 至少 3 个正常公开仓库 analyze 成功。
- QA 成功率 >= 90%。
- evidence 覆盖率 >= 85%。
- command hallucination = 0。
- SelfCheck 缺失率 = 0。
- 无 open issues 仓库能生成 internal first tasks。
- 用户页不展示 raw debug 信息。
- 调试页能展示完整 trace。
- 不出现 API Key 泄露。
"""


def known_limitations_doc(report: dict[str, Any]) -> str:
    lines = ["# RepoMentor 已知限制", ""]
    lines.extend([f"- {item}" for item in report.get("known_limitations", [])])
    lines.append("")
    return "\n".join(lines)


def upgrade_recommendations_doc(report: dict[str, Any]) -> str:
    lines = ["# RepoMentor 下一阶段升级建议", ""]
    for priority, items in report.get("upgrade_recommendations", {}).items():
        lines.append(f"## {priority}")
        lines.extend([f"- {item}" for item in items])
        lines.append("")
    return "\n".join(lines)


def apply_repository_pass_fail(record: dict[str, Any]) -> None:
    record["pass"] = record.get("analyze_status") == "success" and not record.get("errors")


def graph_commands(graph: dict[str, Any]) -> set[str]:
    commands = set()
    for values in (graph.get("commands") or {}).values():
        for command in values or []:
            commands.add(normalize_command(command))
    for item in graph.get("quality_commands", []):
        if item.get("command"):
            commands.add(normalize_command(item["command"]))
    return commands


def normalize_command(command: str) -> str:
    return re.sub(r"\s+", " ", (command or "").replace("\\", "/")).strip()


def file_path_known(path: str, files: set[str]) -> bool:
    normalized = path.replace("\\", "/").removeprefix("./")
    return normalized in files or any(file.endswith(f"/{normalized}") for file in files)


def path_is_explicitly_missing(path: str, text: str) -> bool:
    normalized_path = re.escape(path.replace("\\", "/"))
    normalized_text = text.replace("\\", "/")
    patterns = [
        rf"未找到[^。；;\n]{{0,40}}{normalized_path}",
        rf"没有[^。；;\n]{{0,40}}{normalized_path}",
        rf"缺少[^。；;\n]{{0,40}}{normalized_path}",
        rf"no [^.:\n]{{0,40}}{normalized_path}",
        rf"missing [^.:\n]{{0,40}}{normalized_path}",
    ]
    return any(re.search(pattern, normalized_text, re.IGNORECASE) for pattern in patterns)


def count_files(files: list[dict[str, Any]], types: set[str]) -> int:
    return sum(1 for item in files if item.get("file_type") in types)


def looks_like_code_repo(files: list[dict[str, Any]]) -> bool:
    return any((item.get("extension") or "").lower() in {".py", ".js", ".jsx", ".ts", ".tsx"} for item in files)


def readable_error(body: Any) -> str:
    if isinstance(body, dict):
        detail = body.get("detail", body)
        return json.dumps(detail, ensure_ascii=False) if isinstance(detail, (dict, list)) else str(detail)
    return str(body)


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return SECRET_RE.sub("[redacted-api-key]", value)
    return value


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = (len(values) - 1) * (p / 100)
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return values[int(index)]
    return values[lower] * (upper - index) + values[upper] * (index - lower)


def percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def infer_repo_id_from_answer(body: dict[str, Any]) -> str:
    trace = " ".join(body.get("trace_summary", []))
    match = re.search(r"repo_id=([A-Za-z0-9_-]+)", trace)
    return match.group(1) if match else ""


if __name__ == "__main__":
    raise SystemExit(main())

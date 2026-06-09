from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


API_BASE = os.getenv("REPOMENTOR_API_BASE", "http://127.0.0.1:8000/api")
REPO_URL = os.getenv("SMOKE_REPO_URL", "https://github.com/huier5635-cmd/resilience-copilot-gemma4")
REPORT_PATH = Path(__file__).with_name("smoke_test_report.md")


def request_json(path: str, method: str = "GET", payload: dict[str, Any] | None = None, timeout: int = 180) -> Any:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(f"{API_BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def field_status(payload: dict[str, Any], field: str) -> str:
    value: Any = payload
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            return "missing"
        value = value[part]
    if value in (None, "", [], {}):
        return "empty"
    return "ok"


def length_of(payload: dict[str, Any], field: str) -> int:
    value: Any = payload
    for part in field.split("."):
        if not isinstance(value, dict):
            return 0
        value = value.get(part)
    return len(value) if hasattr(value, "__len__") and not isinstance(value, str) else int(bool(value))


def row(name: str, status: str, detail: str = "") -> str:
    return f"| {name} | {status} | {detail} |"


def entrypoint_path(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return str(item.get("path") or "")
    return ""


def normalize_command(command: str) -> str:
    return " ".join(command.replace("\\", "/").split())


def main(provider: str = "current") -> int:
    lines = [
        "# RepoMentor Smoke Test Report",
        "",
        f"- API base: `{API_BASE}`",
        f"- Repo URL: `{REPO_URL}`",
        f"- Requested LLM provider: `{provider}`",
        f"- Generated at: `{time.strftime('%Y-%m-%d %H:%M:%S')}`",
        "",
    ]
    failures: list[str] = []

    try:
        health = request_json("/health", timeout=10)
        lines.extend(["## Health", "", "| Check | Status | Detail |", "| --- | --- | --- |"])
        lines.append(row("health", "ok" if health.get("status") == "ok" else "fail", json.dumps(health, ensure_ascii=False)))
        lines.append("")
    except Exception as error:
        lines.extend(["## Health", "", row("health", "fail", str(error)), ""])
        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
        return 1

    endpoints: dict[str, dict[str, Any]] = {}
    try:
        analyze = request_json("/repos/analyze", method="POST", payload={"repo_url": REPO_URL}, timeout=240)
        repo_id = analyze["repo_id"]
        session_id = analyze["session_id"]
        endpoints["analyze"] = analyze
        endpoints["graph"] = request_json(f"/repos/{repo_id}/graph")
        endpoints["development_workflow"] = request_json(f"/repos/{repo_id}/development-workflow")
        endpoints["learning_path"] = request_json(f"/repos/{repo_id}/learning-path")
        endpoints["issues"] = request_json(f"/repos/{repo_id}/issues/recommend")
        endpoints["qa"] = request_json(f"/repos/{repo_id}/qa", method="POST", payload={"question": "这个项目怎么启动？"})
        endpoints["memory"] = request_json(f"/debug/session/{session_id}/memory")
    except (KeyError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        failures.append(f"API request failed: {error}")

    checks = {
        "analyze": [
            "repo_id",
            "repo_url",
            "owner",
            "name",
            "files",
            "graph_summary.files",
            "graph_summary.symbols",
            "graph_summary.docs",
            "languages",
            "key_files",
            "entrypoints",
            "setup_commands",
            "run_commands",
            "test_commands",
            "worker_outputs",
            "issues_count",
        ],
        "graph": ["files", "symbols", "docs", "languages", "key_files", "entrypoints", "commands.setup", "commands.run", "commands.test"],
        "development_workflow": ["setup_steps", "development_commands", "test_commands", "new_contributor_checklist"],
        "learning_path": ["steps", "verifiable_commands"],
        "issues": ["issues", "message"],
        "qa": ["conclusion", "steps", "risks", "verifiable_commands", "self_check", "model_info"],
        "memory": ["retrieved_evidence", "worker_outputs", "final_decision_trace"],
    }

    for endpoint_name, fields in checks.items():
        payload = endpoints.get(endpoint_name, {})
        lines.extend([f"## {endpoint_name}", "", "| Field | Status | Count/Detail |", "| --- | --- | --- |"])
        for field in fields:
            status = field_status(payload, field)
            count = length_of(payload, field)
            if status in {"missing", "empty"} and field not in {"issues", "message"}:
                failures.append(f"{endpoint_name}.{field} is {status}")
            lines.append(row(field, status, str(count)))
        lines.append("")

    graph = endpoints.get("graph", {})
    analyze = endpoints.get("analyze", {})
    issues = endpoints.get("issues", {})
    qa = endpoints.get("qa", {})
    memory = endpoints.get("memory", {})
    files = graph.get("files", [])
    symbols = graph.get("symbols", [])
    docs_files = graph.get("docs", [])
    test_files = [item for item in files if item.get("file_type") == "test"]
    entrypoints = graph.get("entrypoints", [])
    entrypoint_paths = [entrypoint_path(item) for item in entrypoints]
    test_edges = graph.get("tests", [])
    graph_edges = graph.get("raw_graph", {}).get("edges", []) or graph.get("edges", [])
    doc_edges = [edge for edge in graph_edges if edge.get("edge_type") in {"documents", "mentions"}]
    quality_commands = graph.get("quality_commands", [])
    backend_keys = [
        (item.get("command_type"), normalize_command(item.get("command", "")))
        for item in quality_commands
    ]
    visible_command_keys = [
        (item.get("command_type"), normalize_command(item.get("command", "")))
        for item in quality_commands
    ]
    worker_evidence_count = sum(len(output.get("evidence", [])) for output in memory.get("worker_outputs", []))
    memory_evidence_count = len(memory.get("retrieved_evidence", []))
    model_info = qa.get("model_info", {}) if isinstance(qa, dict) else {}

    deterministic_checks = [
        ("files > 0", len(files) > 0, str(len(files))),
        ("symbols > 0", len(symbols) > 0, str(len(symbols))),
        ("docs > 0", len(docs_files) > 0, str(len(docs_files))),
        (
            "entrypoints not only __init__.py",
            bool(entrypoint_paths) and any(not path.endswith("__init__.py") for path in entrypoint_paths),
            " | ".join(entrypoint_paths[:8]),
        ),
        ("test files imply test edges", not test_files or len(test_edges) > 0, f"test_files={len(test_files)}, test_edges={len(test_edges)}"),
        ("docs files imply doc edges", not docs_files or len(doc_edges) > 0, f"docs={len(docs_files)}, doc_edges={len(doc_edges)}"),
        ("backend quality command keys are deduped", len(backend_keys) == len(set(backend_keys)), f"commands={len(quality_commands)}"),
        (
            "visible command duplication is bounded",
            len(quality_commands) <= max(1, len(set(visible_command_keys)) * 3),
            f"commands={len(quality_commands)}, visible_unique={len(set(visible_command_keys))}",
        ),
        (
            "shared memory evidence covers worker evidence",
            memory_evidence_count >= worker_evidence_count,
            f"memory={memory_evidence_count}, worker_evidence={worker_evidence_count}",
        ),
        (
            "issue fallback generated when open issues are zero",
            analyze.get("issues_count", 0) > 0 or any(item.get("source") == "internal_suggestion" for item in issues.get("issues", [])),
            f"issues_count={analyze.get('issues_count')}, recommendations={len(issues.get('issues', []))}",
        ),
        (
            "FinalAnswer JSON includes model_info",
            isinstance(model_info, dict) and bool(model_info.get("provider")),
            json.dumps(model_info, ensure_ascii=False),
        ),
    ]

    lines.extend(["## Deterministic Quality Checks", "", "| Check | Status | Detail |", "| --- | --- | --- |"])
    for name, passed, detail in deterministic_checks:
        lines.append(row(name, "ok" if passed else "fail", detail))
        if not passed:
            failures.append(name)
    lines.append("")

    lines.extend(
        [
            "## QA LLM Provider",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| provider | `{model_info.get('provider', '')}` |",
            f"| model | `{model_info.get('model', '')}` |",
            f"| prompt_type | `{model_info.get('prompt_type', '')}` |",
            f"| evidence_count | `{model_info.get('evidence_count', '')}` |",
            f"| used_llm | `{model_info.get('used_llm', '')}` |",
            f"| fallback_to_mock | `{model_info.get('fallback_to_mock', '')}` |",
            f"| elapsed_ms | `{model_info.get('elapsed_ms', '')}` |",
            "",
            "Run this script once with `--provider mock` and once after restarting the backend with `LLM_PROVIDER=deepseek` to compare mock vs DeepSeek QA output.",
            "",
        ]
    )

    if provider != "current":
        returned_provider = model_info.get("provider")
        if returned_provider and returned_provider != provider:
            failures.append(f"requested provider {provider} but backend reported {returned_provider}")

    if failures:
        lines.extend(["## Failures", "", *[f"- {item}" for item in failures], ""])
    else:
        lines.extend(["## Result", "", "All deterministic structure checks passed.", ""])

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RepoMentor smoke checks.")
    parser.add_argument("--provider", choices=["current", "mock", "deepseek"], default="current")
    args = parser.parse_args()
    sys.exit(main(args.provider))

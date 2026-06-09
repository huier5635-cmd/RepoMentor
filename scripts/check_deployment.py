from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_-]{16,}|[A-Za-z0-9_-]{32,})")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
DEFAULT_TEST_REPO = "https://github.com/octocat/Hello-World"


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Check RepoMentor online deployment.")
    parser.add_argument("--frontend-url", required=True, help="Public frontend URL, for example https://app.vercel.app")
    parser.add_argument("--backend-url", required=True, help="Public backend origin, for example https://api.onrender.com")
    parser.add_argument("--repo-url", default=DEFAULT_TEST_REPO, help="Small public repo used for POST /api/repos/analyze.")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--skip-analyze", action="store_true", help="Skip POST /api/repos/analyze when checking cold deployments.")
    args = parser.parse_args()

    frontend_url = normalize_origin(args.frontend_url)
    backend_url = normalize_origin(args.backend_url)
    results: list[CheckResult] = []

    health = get_json(f"{backend_url}/api/health", timeout=20)
    results.append(CheckResult("backend /api/health", health.ok, health.detail))

    model_status = get_json(f"{backend_url}/api/model/status", timeout=20)
    status_payload = model_status.payload if isinstance(model_status.payload, dict) else {}
    leaked = bool(SECRET_RE.search(json.dumps(status_payload, ensure_ascii=False)))
    results.append(CheckResult("backend /api/model/status", model_status.ok and not leaked, "no raw API key detected" if model_status.ok and not leaked else model_status.detail))

    frontend = get_text(frontend_url, timeout=20)
    results.append(CheckResult("frontend URL", frontend.ok, frontend.detail))

    cors = check_cors(backend_url, frontend_url)
    results.append(cors)

    frontend_host = urllib.parse.urlparse(frontend_url).hostname or ""
    backend_host = urllib.parse.urlparse(backend_url).hostname or ""
    non_local = frontend_host not in LOCAL_HOSTS and backend_host not in LOCAL_HOSTS
    results.append(
        CheckResult(
            "public URL check",
            non_local,
            "frontend/backend are public-looking origins" if non_local else "frontend-url or backend-url is localhost/127.0.0.1; do not submit it as an online demo URL",
        )
    )

    bundle_check = check_frontend_assets_for_localhost(frontend_url, frontend.text if frontend.ok else "")
    results.append(bundle_check)

    provider_active = status_payload.get("provider_active") or status_payload.get("provider")
    if provider_active == "mock":
        results.append(CheckResult("LLM mode", True, "mock demo mode; no model cost by default"))
    else:
        results.append(CheckResult("LLM mode", True, f"provider_active={provider_active}; confirm API key is configured in platform env only"))

    if args.skip_analyze:
        results.append(CheckResult("POST /api/repos/analyze", True, "skipped by --skip-analyze"))
    else:
        analyze = post_json(
            f"{backend_url}/api/repos/analyze",
            {"repo_url": args.repo_url},
            timeout=args.timeout,
        )
        analyze_ok = analyze.ok and isinstance(analyze.payload, dict) and bool(analyze.payload.get("repo_id"))
        detail = f"repo_id={analyze.payload.get('repo_id')}" if analyze_ok else analyze.detail
        results.append(CheckResult("POST /api/repos/analyze", analyze_ok, detail))

    report_path = Path("reports/deployment_check.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(frontend_url, backend_url, results), encoding="utf-8")
    print(f"Wrote {report_path}")
    return 0 if all(item.ok for item in results) else 1


class Response:
    def __init__(self, ok: bool, detail: str, payload: Any = None, text: str = "") -> None:
        self.ok = ok
        self.detail = detail
        self.payload = payload
        self.text = text


def normalize_origin(value: str) -> str:
    return value.strip().rstrip("/")


def get_json(url: str, timeout: int) -> Response:
    response = get_text(url, timeout)
    if not response.ok:
        return response
    try:
        return Response(True, "HTTP 200 JSON", json.loads(response.text), response.text)
    except json.JSONDecodeError as error:
        return Response(False, f"invalid JSON: {error}", text=response.text)


def get_text(url: str, timeout: int) -> Response:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            ok = 200 <= response.status < 300
            return Response(ok, f"HTTP {response.status}", text=text)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        return Response(False, f"HTTP {error.code}: {body[:240]}", text=body)
    except Exception as error:
        return Response(False, str(error))


def post_json(url: str, payload: dict[str, Any], timeout: int) -> Response:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            return Response(200 <= response.status < 300, f"HTTP {response.status}", parsed, text)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        return Response(False, f"HTTP {error.code}: {body[:240]}", text=body)
    except Exception as error:
        return Response(False, str(error))


def check_cors(backend_url: str, frontend_url: str) -> CheckResult:
    request = urllib.request.Request(
        f"{backend_url}/api/health",
        headers={
            "Origin": frontend_url,
            "Access-Control-Request-Method": "GET",
        },
        method="OPTIONS",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            allowed_origin = response.headers.get("access-control-allow-origin", "")
            ok = response.status in {200, 204} and allowed_origin in {frontend_url, "*"}
            detail = f"allow-origin={allowed_origin or 'missing'}"
            return CheckResult("CORS frontend -> backend", ok, detail)
    except Exception as error:
        return CheckResult("CORS frontend -> backend", False, str(error))


def check_frontend_assets_for_localhost(frontend_url: str, html: str) -> CheckResult:
    if not html:
        return CheckResult("frontend bundle API origin", False, "frontend HTML unavailable")
    asset_paths = re.findall(r'<script[^>]+src="([^"]+\.js)"', html)
    texts = [html]
    for path in asset_paths[:5]:
        asset_url = urllib.parse.urljoin(frontend_url + "/", path)
        response = get_text(asset_url, timeout=20)
        if response.ok:
            texts.append(response.text)
    haystack = "\n".join(texts)
    has_local_backend = "localhost:8000" in haystack or "127.0.0.1:8000" in haystack
    return CheckResult(
        "frontend bundle API origin",
        not has_local_backend,
        "no localhost backend URL in frontend bundle" if not has_local_backend else "frontend bundle contains localhost backend URL",
    )


def render_report(frontend_url: str, backend_url: str, results: list[CheckResult]) -> str:
    lines = [
        "# RepoMentor Deployment Check",
        "",
        f"- Frontend URL: `{frontend_url}`",
        f"- Backend URL: `{backend_url}`",
        "",
        "| Check | Result | Detail |",
        "| --- | --- | --- |",
    ]
    for item in results:
        lines.append(f"| {item.name} | {'PASS' if item.ok else 'FAIL'} | {item.detail.replace('|', '/')} |")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `127.0.0.1` and `localhost` are valid only for local Docker/dev runs, not for online submission URLs.",
            "- Online demo should default to `LLM_PROVIDER=mock` unless you intentionally configure a private DeepSeek key in the hosting platform.",
            "- Do not paste API keys into this report.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())

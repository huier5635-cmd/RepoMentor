# RepoMentor Smoke Test Report

- API base: `http://127.0.0.1:8000/api`
- Repo URL: `https://github.com/huier5635-cmd/resilience-copilot-gemma4`
- Requested LLM provider: `mock`
- Generated at: `2026-06-09 12:15:56`

## Health

| Check | Status | Detail |
| --- | --- | --- |
| health | ok | {"status": "ok"} |

## analyze

| Field | Status | Count/Detail |
| --- | --- | --- |
| repo_id | ok | 1 |
| repo_url | ok | 1 |
| owner | ok | 1 |
| name | ok | 1 |
| files | ok | 64 |
| graph_summary.files | ok | 1 |
| graph_summary.symbols | ok | 1 |
| graph_summary.docs | ok | 1 |
| languages | ok | 9 |
| key_files | ok | 2 |
| entrypoints | ok | 14 |
| setup_commands | ok | 1 |
| run_commands | ok | 6 |
| test_commands | ok | 2 |
| worker_outputs | ok | 8 |
| issues_count | ok | 0 |

## graph

| Field | Status | Count/Detail |
| --- | --- | --- |
| files | ok | 64 |
| symbols | ok | 221 |
| docs | ok | 20 |
| languages | ok | 9 |
| key_files | ok | 2 |
| entrypoints | ok | 14 |
| commands.setup | ok | 1 |
| commands.run | ok | 6 |
| commands.test | ok | 2 |

## development_workflow

| Field | Status | Count/Detail |
| --- | --- | --- |
| setup_steps | ok | 2 |
| development_commands | ok | 1 |
| test_commands | ok | 2 |
| new_contributor_checklist | ok | 4 |

## learning_path

| Field | Status | Count/Detail |
| --- | --- | --- |
| steps | ok | 7 |
| verifiable_commands | ok | 8 |

## issues

| Field | Status | Count/Detail |
| --- | --- | --- |
| issues | ok | 6 |
| message | ok | 1 |

## qa

| Field | Status | Count/Detail |
| --- | --- | --- |
| conclusion | ok | 1 |
| steps | ok | 6 |
| risks | ok | 1 |
| verifiable_commands | ok | 9 |
| self_check | ok | 6 |
| model_info | ok | 9 |

## memory

| Field | Status | Count/Detail |
| --- | --- | --- |
| retrieved_evidence | ok | 10 |
| worker_outputs | ok | 8 |
| final_decision_trace | ok | 9 |

## Deterministic Quality Checks

| Check | Status | Detail |
| --- | --- | --- |
| files > 0 | ok | 64 |
| symbols > 0 | ok | 221 |
| docs > 0 | ok | 20 |
| entrypoints not only __init__.py | ok | scripts/run_academic_eval.py | scripts/run_demo.py | scripts/run_eval.py | scripts/run_local_validation.py | scripts/run_stress_test.py | src/agent/__main__.py | app.js | src/__init__.py |
| test files imply test edges | ok | test_files=6, test_edges=15 |
| docs files imply doc edges | ok | docs=20, doc_edges=50 |
| backend quality command keys are deduped | ok | commands=9 |
| visible command duplication is bounded | ok | commands=9, visible_unique=9 |
| shared memory evidence covers worker evidence | ok | memory=10, worker_evidence=10 |
| issue fallback generated when open issues are zero | ok | issues_count=0, recommendations=6 |
| FinalAnswer JSON includes model_info | ok | {"provider": "mock", "model": "mock-deterministic", "prompt_type": "setup_run", "evidence_count": 10, "elapsed_ms": 0.0, "success": true, "used_llm": false, "fallback_to_mock": false, "error_message": ""} |

## QA LLM Provider

| Field | Value |
| --- | --- |
| provider | `mock` |
| model | `mock-deterministic` |
| prompt_type | `setup_run` |
| evidence_count | `10` |
| used_llm | `False` |
| fallback_to_mock | `False` |
| elapsed_ms | `0.0` |

Run this script once with `--provider mock` and once after restarting the backend with `LLM_PROVIDER=deepseek` to compare mock vs DeepSeek QA output.

## Result

All deterministic structure checks passed.

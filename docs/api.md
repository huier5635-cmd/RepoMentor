# API

## POST `/api/repos/analyze`

Input:

```json
{ "repo_url": "https://github.com/owner/repo" }
```

Output includes `repo_id`, graph summary, worker outputs, commands, entrypoints and `session_id`.

## GET `/api/repos/{repo_id}/graph`

Returns files, symbols, imports, tests, docs, build scripts, development workflow, quality commands, contributing rules, CI rules, entrypoints, commands and index summary.

## POST `/api/repos/{repo_id}/qa`

Input:

```json
{ "question": "这个仓库怎么启动？" }
```

Returns `FinalAnswer` with conclusion, docs/code/issues evidence, steps, risks, verifiable commands, self-check and trace summary.

## GET `/api/repos/{repo_id}/learning-path`

Returns a learning path derived from docs, entrypoints, symbols, tests and development workflow guidance.

## GET `/api/repos/{repo_id}/development-workflow`

Returns structured development workflow guidance:

- setup steps
- development/test/lint/format/type-check/build commands
- branch and commit rules
- PR workflow
- CI rules
- code style rules
- new contributor checklist
- evidence, risks, verifiable commands and self-check

## GET `/api/repos/{repo_id}/issues/recommend`

Returns issue recommendations grounded in real GitHub issues.

## GET `/api/memory/{session_id}`

Returns shared working memory and trace.

# Development Workflow Worker

## Design Goal

Development Workflow Worker extracts the project-specific development process and code quality rules for new contributors. It is intentionally separate from Docs Worker: Docs Worker parses general documentation, while Development Workflow Worker turns contribution, CI and quality signals into structured guidance.

## Input Sources

- `RepoSnapshot`
- `RepositoryIntelligenceGraph`
- docs chunks from README, docs and examples
- config files such as `package.json`, `pyproject.toml`, `setup.cfg`, `tox.ini`, `pytest.ini`
- build files such as `Makefile`, `Dockerfile`, `docker-compose.yml`
- GitHub Actions files in `.github/workflows/*`
- PR templates in `.github/PULL_REQUEST_TEMPLATE*`
- style configs such as `.prettierrc`, `.eslintrc`, `eslint.config.*`, `ruff.toml`, `.flake8`, `mypy.ini`, pre-commit and commitlint configs

## Extracted Fields

The worker outputs `DevelopmentWorkflowGuide`:

- setup steps
- development, test, lint, format, type-check and build commands
- branch rules
- commit rules
- pull request workflow
- CI rules
- code style rules
- contribution steps
- new contributor checklist
- evidence and uncertainties

## Command Detection

Commands are accepted when they are found in repository evidence:

- docs command blocks or command-like lines
- package scripts
- `pyproject.toml` tool sections
- Makefile targets
- GitHub Actions `run:` steps

The command is classified as `setup`, `dev`, `test`, `lint`, `format`, `type_check`, `build`, `ci` or `unknown`. Commands from config and CI get higher confidence than command-like text from prose.

## Code Style Rules

Style rules are inferred only from evidence such as lint or format scripts, ruff, black, eslint, prettier, flake8, mypy or pre-commit configs, and explicit documentation. When no style evidence exists, the worker emits an uncertainty instead of inventing a convention.

## PR Workflow

PR workflow extraction uses PR templates, CONTRIBUTING / README references to issues, review, maintainers, screenshots, benchmarks or checklist items, and CI workflow triggers for `pull_request`. If no PR template exists, the guide marks that as an uncertainty.

## Integration

- LearningPath includes a “Development Workflow and Code Style” stage.
- Issue recommendation can use the checklist and quality commands as suggested first steps.
- SelfCheck verifies that commands and rules mentioned in final answers are grounded in docs/config/CI evidence.

## Current Limits

- YAML parsing is regex-based in the MVP.
- JS/TS and Python command inference is deterministic but conservative.
- Branch and commit rules are only emitted when explicit evidence exists.
- Required CI checks are inferred from workflow triggers, not from GitHub branch protection rules.

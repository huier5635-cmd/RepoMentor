# RepoMentor Architecture

RepoMentor follows a single orchestrator plus multiple specialized workers.

```mermaid
flowchart TD
  User["User question"] --> Router["Intent Router / Orchestrator"]
  Router --> Planner["Task Planner"]
  Planner --> RepoGraph["Repo Graph Worker"]
  Planner --> Symbol["Symbol Worker"]
  Planner --> Dependency["Dependency Worker"]
  Planner --> Docs["Docs Worker"]
  Planner --> Issue["Issue Worker"]
  Planner --> Test["Test Worker"]
  Planner --> Code["Code Explanation Worker"]
  Planner --> Workflow["Development Workflow Worker"]
  RepoGraph --> Memory["Shared Working Memory"]
  Symbol --> Memory
  Dependency --> Memory
  Docs --> Memory
  Issue --> Memory
  Test --> Memory
  Code --> Memory
  Workflow --> Memory
  Memory --> Candidate["Candidate Answer Generator"]
  Candidate --> Evaluator["Evaluator"]
  Evaluator --> Optimizer["Optimizer"]
  Optimizer --> Final["Evidence-grounded Final Answer"]
```

Repository facts must come from deterministic parsers, GitHub API responses, file content, CI/config files, or retrieval evidence. LLM-like generation is isolated behind `llm_service.py` and is mocked in the MVP.

## Code Mapping

- `backend/app/core/orchestrator.py`: routes tasks, runs workers, builds memory and final answers.
- `backend/app/workers/*`: independent worker classes.
- `backend/app/workers/development_workflow_worker.py`: extracts contribution workflow, quality commands, PR templates and CI rules.
- `backend/app/data_layer/repository_intelligence_graph.py`: structured repository fact layer.
- `backend/app/data_layer/hybrid_retrieval_index.py`: keyword + vector fallback + metadata retrieval.
- `backend/app/answer/*`: candidate generation, evaluation, optimization, evidence formatting.
- `frontend/src/components/DevelopmentWorkflowPanel.jsx`: workflow and code-style panel for new contributors.

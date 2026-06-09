# Agent Flow

RepoMentor is intentionally not an open multi-agent chat. It presents multiple agent-like workers, but execution is controlled by a single `Orchestrator`.

## Analyze Flow

1. Clone or open the repository.
2. Run `RepoGraphWorker`.
3. Run `SymbolWorker`.
4. Run `DependencyWorker`.
5. Run `DocsWorker`.
6. Run `IssueWorker`.
7. Run `TestWorker`.
8. Run `CodeExplanationWorker` for an initial graph-aware pass.
9. Run `DevelopmentWorkflowWorker` to extract contribution process, quality commands, PR templates and CI checks.
10. Store all worker outputs in `SharedWorkingMemory`.
11. Build the hybrid retrieval index.

## QA Flow

1. `IntentRouter` classifies the question.
2. `TaskPlanner` chooses lookup or worker steps.
3. `HybridRetrievalIndex` retrieves evidence.
4. Optional task-specific worker output is added to memory.
5. `CandidateAnswerGenerator` builds `AnswerBundle`.
6. `Evaluator` checks evidence coverage and command grounding.
7. `Optimizer` lowers confidence or removes unsupported claims.
8. `EvidenceFormatter` returns `FinalAnswer`.

For contribution questions such as “这个仓库如何参与贡献？”, the orchestrator reuses Docs, Issue, Test and Development Workflow worker outputs before generating the final answer.

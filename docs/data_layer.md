# Data Layer

The data layer has three parts.

## Repository Intelligence Graph

`RepositoryIntelligenceGraph` stores:

- files
- symbols
- imports
- tests
- docs
- build scripts
- development workflow guide
- quality commands
- contributing rules
- CI rules
- entrypoints
- run/test/build commands
- graph edges

`RepositoryIntelligenceGraphStore` provides query methods such as `get_file`, `find_symbol`, `get_imports`, `get_imported_by`, `get_tests_for_file`, `get_docs_for_file`, `get_development_workflow`, `get_quality_commands`, `get_contributing_rules`, `get_ci_rules`, `get_new_contributor_checklist`, and `get_related_context`.

## Hybrid Retrieval Index

The MVP retrieval layer contains:

- `KeywordIndex`: exact-ish token lookup over filenames, symbols, commands, docs, workflow facts and issue labels.
- `VectorIndex`: simple similarity fallback placeholder.
- `MetadataFilter`: source type, language, file type, label, command type and rule type filters.
- `HybridRetrievalIndex`: merges, deduplicates and ranks retrieval results.

## Shared Working Memory

`SharedWorkingMemoryStore` records:

- current task
- user question
- retrieved evidence
- intermediate conclusions
- unresolved uncertainties
- worker outputs
- development workflow findings
- quality commands
- contributing rules
- CI findings
- workflow uncertainties
- final decision trace

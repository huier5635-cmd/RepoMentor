from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class FileType(str, Enum):
    SOURCE = "source"
    SOURCE_FRONTEND = "source_frontend"
    SOURCE_FRONTEND_STYLE = "source_frontend_style"
    TEST = "test"
    DOCS = "docs"
    DOCS_LEGAL = "docs_legal"
    DOCS_REFERENCE = "docs_reference"
    DOCS_STATIC = "docs_static"
    CONFIG = "config"
    DATA = "data"
    BUILD = "build"
    ISSUE = "issue"
    UNKNOWN = "unknown"


class SymbolType(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    INTERFACE = "interface"
    UNKNOWN = "unknown"


class EdgeType(str, Enum):
    IMPORTS = "imports"
    CALLS = "calls"
    TESTS = "tests"
    DOCUMENTS = "documents"
    MENTIONS = "mentions"
    BUILDS = "builds"
    DEFINES = "defines"
    CONFIGURES = "configures"


class SourceType(str, Enum):
    DOCS = "docs"
    CODE = "code"
    GRAPH = "graph"
    ISSUE = "issue"
    ISSUES = "issues"
    TEST = "test"
    TESTS = "tests"
    CONFIG = "config"
    BUILD = "build"
    COMMAND = "command"
    WORKFLOW = "workflow"
    CONTRIBUTING = "contributing"
    CI = "ci"
    STYLE = "style"
    PR_TEMPLATE = "pr_template"
    INTERNAL_SUGGESTION = "internal_suggestion"


class WorkerStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class TaskType(str, Enum):
    REPO_OVERVIEW = "repo_overview"
    SETUP_RUN = "setup_run"
    CODE_EXPLANATION = "code_explanation"
    LEARNING_PATH = "learning_path"
    ISSUE_RECOMMENDATION = "issue_recommendation"
    TEST_MAPPING = "test_mapping"
    DEVELOPMENT_WORKFLOW = "development_workflow"
    GENERAL_QA = "general_qa"


class SuggestedAction(str, Enum):
    ACCEPT = "accept"
    RETRIEVE_MORE = "retrieve_more"
    REVISE = "revise"
    LOWER_CONFIDENCE = "lower_confidence"
    REFUSE = "refuse"


class CommandType(str, Enum):
    SETUP = "setup"
    DEV = "dev"
    TEST = "test"
    LINT = "lint"
    FORMAT = "format"
    TYPE_CHECK = "type_check"
    BUILD = "build"
    CI = "ci"
    UNKNOWN = "unknown"


class RuleType(str, Enum):
    BRANCH = "branch"
    COMMIT = "commit"
    STYLE = "style"
    TEST = "test"
    DOCS = "docs"
    REVIEW = "review"
    ISSUE = "issue"
    CONTRIBUTION = "contribution_rule"
    CODE_STYLE = "code_style_rule"
    PR = "pr_rule"
    CI = "ci_rule"
    PROJECT_SAFETY_POLICY = "project_safety_policy"
    DOCUMENTATION_REFERENCE = "documentation_reference"
    TEST_RULE = "test_rule"
    SETUP_RULE = "setup_rule"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ModelInfo(BaseModel):
    provider: str = "mock"
    model: str = "mock-deterministic"
    prompt_type: str = "general"
    evidence_count: int = 0
    elapsed_ms: float = 0.0
    success: bool = True
    used_llm: bool = False
    fallback_to_mock: bool = False
    error_message: str = ""


class FileNode(BaseModel):
    path: str
    name: str
    extension: str = ""
    language: str = "unknown"
    file_type: FileType = FileType.UNKNOWN
    size: int = 0
    content_preview: str = ""
    line_count: int = 0


class SymbolNode(BaseModel):
    name: str
    symbol_type: SymbolType = SymbolType.UNKNOWN
    file_path: str
    line_start: int = 1
    line_end: int = 1
    signature: str = ""
    docstring: str = ""
    language: str = "unknown"


class GraphEdge(BaseModel):
    source: str
    target: str
    edge_type: EdgeType
    evidence: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class IssueCard(BaseModel):
    issue_number: int
    title: str
    body: str = ""
    labels: list[str] = Field(default_factory=list)
    comments_count: int = 0
    created_at: str = ""
    updated_at: str = ""
    author_association: str = ""
    issue_type: str = "unknown"
    url: str = ""
    difficulty: str = "unknown"
    skill_tags: list[str] = Field(default_factory=list)
    recommendation_score: float = 0.0


class QualityCommand(BaseModel):
    name: str
    command: str
    command_type: CommandType = CommandType.UNKNOWN
    source_file: str
    line_start: int | None = None
    line_end: int | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    evidence_sources: list[str] = Field(default_factory=list)


class EntryPointCandidate(BaseModel):
    path: str
    reason: str
    source: str
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class ContributingRule(BaseModel):
    rule_type: RuleType = RuleType.UNKNOWN
    description: str
    source_file: str
    evidence: list["EvidenceItem"] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class PullRequestWorkflow(BaseModel):
    steps: list[str] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    required_checks: list[str] = Field(default_factory=list)
    source_file: str
    evidence: list["EvidenceItem"] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class CIRule(BaseModel):
    workflow_file: str
    workflow_name: str | None = None
    triggers: list[str] = Field(default_factory=list)
    jobs: list[str] = Field(default_factory=list)
    commands: list[QualityCommand] = Field(default_factory=list)
    required_for_pr: bool | None = None
    evidence: list["EvidenceItem"] = Field(default_factory=list)


class DevelopmentWorkflowGuide(BaseModel):
    repo_id: str
    quality_commands: list[QualityCommand] = Field(default_factory=list)
    setup_steps: list[str] = Field(default_factory=list)
    development_commands: list[QualityCommand] = Field(default_factory=list)
    test_commands: list[QualityCommand] = Field(default_factory=list)
    lint_commands: list[QualityCommand] = Field(default_factory=list)
    format_commands: list[QualityCommand] = Field(default_factory=list)
    type_check_commands: list[QualityCommand] = Field(default_factory=list)
    build_commands: list[QualityCommand] = Field(default_factory=list)
    branch_rules: list[ContributingRule] = Field(default_factory=list)
    commit_rules: list[ContributingRule] = Field(default_factory=list)
    contribution_rules: list[ContributingRule] = Field(default_factory=list)
    pull_request_rules: list[PullRequestWorkflow] = Field(default_factory=list)
    ci_rules: list[CIRule] = Field(default_factory=list)
    code_style_rules: list[ContributingRule] = Field(default_factory=list)
    setup_rules: list[ContributingRule] = Field(default_factory=list)
    test_rules: list[ContributingRule] = Field(default_factory=list)
    documentation_references: list[ContributingRule] = Field(default_factory=list)
    project_safety_policies: list[ContributingRule] = Field(default_factory=list)
    contribution_steps: list[str] = Field(default_factory=list)
    new_contributor_checklist: list[str] = Field(default_factory=list)
    evidence: list["EvidenceItem"] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class RepoSnapshot(BaseModel):
    repo_id: str
    repo_url: str
    local_path: str
    owner: str = ""
    name: str = ""
    default_branch: str = "main"
    files: list[FileNode] = Field(default_factory=list)
    key_files: list[str] = Field(default_factory=list)
    issues: list[IssueCard] = Field(default_factory=list)


class RepositoryIntelligenceGraph(BaseModel):
    files: list[FileNode] = Field(default_factory=list)
    symbols: list[SymbolNode] = Field(default_factory=list)
    imports: list[GraphEdge] = Field(default_factory=list)
    tests: list[GraphEdge] = Field(default_factory=list)
    docs: list[FileNode] = Field(default_factory=list)
    build_scripts: list[FileNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    key_files: list[str] = Field(default_factory=list)
    languages: dict[str, int] = Field(default_factory=dict)
    core_directories: list[str] = Field(default_factory=list)
    entrypoints: list[EntryPointCandidate] = Field(default_factory=list)
    setup_commands: list[str] = Field(default_factory=list)
    run_commands: list[str] = Field(default_factory=list)
    test_commands: list[str] = Field(default_factory=list)
    build_commands: list[str] = Field(default_factory=list)
    lint_commands: list[str] = Field(default_factory=list)
    format_commands: list[str] = Field(default_factory=list)
    type_check_commands: list[str] = Field(default_factory=list)
    development_workflow: DevelopmentWorkflowGuide | None = None
    quality_commands: list[QualityCommand] = Field(default_factory=list)
    contributing_rules: list[ContributingRule] = Field(default_factory=list)
    ci_rules: list[CIRule] = Field(default_factory=list)

    @field_validator("entrypoints", mode="before")
    @classmethod
    def _normalize_legacy_entrypoints(cls, value):
        if not isinstance(value, list):
            return value
        normalized = []
        for item in value:
            if isinstance(item, str):
                normalized.append(
                    {
                        "path": item,
                        "reason": "legacy entrypoint candidate",
                        "source": "legacy graph",
                        "confidence": ConfidenceLevel.LOW.value,
                    }
                )
            else:
                normalized.append(item)
        return normalized


class ChunkDoc(BaseModel):
    chunk_id: str
    source_type: SourceType
    file_path: str = ""
    issue_number: int | None = None
    symbol_name: str = ""
    title: str = ""
    text: str
    line_start: int = 1
    line_end: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    evidence_id: str
    source_type: SourceType
    source_ref: str
    source_path: str = ""
    title: str = ""
    file_path: str = ""
    issue_number: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    quote: str
    snippet: str = ""
    supports_claim: str
    reason: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class WorkerOutput(BaseModel):
    worker_name: str
    task: str
    status: WorkerStatus
    findings: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class SharedWorkingMemory(BaseModel):
    session_id: str
    current_task: str
    user_question: str
    retrieved_evidence: list[EvidenceItem] = Field(default_factory=list)
    intermediate_conclusions: list[str] = Field(default_factory=list)
    unresolved_uncertainties: list[str] = Field(default_factory=list)
    worker_outputs: list[WorkerOutput] = Field(default_factory=list)
    final_decision_trace: list[str] = Field(default_factory=list)
    development_workflow_findings: list[str] = Field(default_factory=list)
    quality_commands: list[QualityCommand] = Field(default_factory=list)
    contributing_rules: list[ContributingRule] = Field(default_factory=list)
    ci_findings: list[str] = Field(default_factory=list)
    workflow_uncertainties: list[str] = Field(default_factory=list)
    model_calls: list[ModelInfo] = Field(default_factory=list)
    final_answer_json: dict[str, Any] = Field(default_factory=dict)


class AnswerBundle(BaseModel):
    conclusion: str
    task_type: TaskType | None = None
    answer_type: str = ""
    evidence: list[EvidenceItem] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    verifiable_commands: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    uncertainties: list[str] = Field(default_factory=list)
    model_info: ModelInfo = Field(default_factory=ModelInfo)
    raw_model_output: str = ""


class SelfCheckReport(BaseModel):
    passed: bool
    evidence_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    hallucination_risks: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    missing_file_uncertainty: list[str] = Field(default_factory=list)
    missing_command_uncertainty: list[str] = Field(default_factory=list)
    hallucinated_file: list[str] = Field(default_factory=list)
    hallucinated_command: list[str] = Field(default_factory=list)
    hallucinated_issue: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    suggested_action: SuggestedAction = SuggestedAction.ACCEPT


class FinalAnswer(BaseModel):
    conclusion: str
    evidence_docs: list[EvidenceItem] = Field(default_factory=list)
    evidence_code: list[EvidenceItem] = Field(default_factory=list)
    evidence_issues: list[EvidenceItem] = Field(default_factory=list)
    evidence_graph: list[EvidenceItem] = Field(default_factory=list)
    evidence_workflow: list[EvidenceItem] = Field(default_factory=list)
    evidence_commands: list[EvidenceItem] = Field(default_factory=list)
    evidence_internal_tasks: list[EvidenceItem] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    verifiable_commands: list[str] = Field(default_factory=list)
    self_check: SelfCheckReport
    trace_summary: list[str] = Field(default_factory=list)
    model_info: ModelInfo = Field(default_factory=ModelInfo)


class RepoGraphWorkerInput(BaseModel):
    repo_id: str
    repo_url: str
    local_path: str
    owner: str = ""
    name: str = ""
    default_branch: str = "main"


class RepoGraphWorkerResult(BaseModel):
    repo_snapshot: RepoSnapshot
    graph: RepositoryIntelligenceGraph
    chunks: list[ChunkDoc] = Field(default_factory=list)
    worker_output: WorkerOutput


class SymbolWorkerInput(BaseModel):
    local_path: str
    files: list[FileNode]


class SymbolWorkerResult(BaseModel):
    symbols: list[SymbolNode]
    edges: list[GraphEdge]
    chunks: list[ChunkDoc] = Field(default_factory=list)
    worker_output: WorkerOutput


class DependencyWorkerInput(BaseModel):
    local_path: str
    files: list[FileNode]


class DependencyWorkerResult(BaseModel):
    imports: list[GraphEdge]
    unresolved_imports: list[str]
    worker_output: WorkerOutput


class DocsWorkerInput(BaseModel):
    local_path: str
    files: list[FileNode]
    graph: RepositoryIntelligenceGraph | None = None


class DocsWorkerResult(BaseModel):
    docs: list[FileNode]
    chunks: list[ChunkDoc]
    edges: list[GraphEdge]
    worker_output: WorkerOutput


class IssueWorkerInput(BaseModel):
    repo_url: str
    owner: str = ""
    name: str = ""


class IssueWorkerResult(BaseModel):
    issues: list[IssueCard]
    chunks: list[ChunkDoc]
    worker_output: WorkerOutput


class TestWorkerInput(BaseModel):
    files: list[FileNode]
    graph: RepositoryIntelligenceGraph


class TestWorkerResult(BaseModel):
    tests: list[GraphEdge]
    test_commands: list[str]
    worker_output: WorkerOutput


class CodeExplanationWorkerInput(BaseModel):
    question: str
    graph: RepositoryIntelligenceGraph
    chunks: list[ChunkDoc] = Field(default_factory=list)


class CodeExplanationWorkerResult(BaseModel):
    output: WorkerOutput


class DevelopmentWorkflowWorkerInput(BaseModel):
    repo_snapshot: RepoSnapshot
    graph: RepositoryIntelligenceGraph
    chunks: list[ChunkDoc] = Field(default_factory=list)


class DevelopmentWorkflowWorkerResult(BaseModel):
    guide: DevelopmentWorkflowGuide
    chunks: list[ChunkDoc] = Field(default_factory=list)
    worker_output: WorkerOutput


class RetrievalFilters(BaseModel):
    source_type: list[str] | None = None
    language: list[str] | None = None
    file_type: list[str] | None = None
    labels: list[str] | None = None
    command_type: list[str] | None = None
    rule_type: list[str] | None = None


class RetrievalResult(BaseModel):
    chunk: ChunkDoc
    evidence: EvidenceItem
    score: float


class AnalyzeRepoRequest(BaseModel):
    repo_url: str


class QARequest(BaseModel):
    question: str


class AnalyzeRepoResponse(BaseModel):
    repo_id: str
    repo_url: str
    owner: str = ""
    name: str = ""
    default_branch: str = "main"
    local_path: str = ""
    status: str
    files: list[FileNode] = Field(default_factory=list)
    file_tree: list[FileNode] = Field(default_factory=list)
    graph_summary: dict[str, Any]
    languages: dict[str, int] = Field(default_factory=dict)
    primary_language: str = ""
    core_directories: list[str] = Field(default_factory=list)
    key_files: list[str] = Field(default_factory=list)
    readme_exists: bool = False
    worker_outputs: list[WorkerOutput]
    setup_commands: list[str] = Field(default_factory=list)
    run_commands: list[str]
    test_commands: list[str]
    build_commands: list[str] = Field(default_factory=list)
    lint_commands: list[str] = Field(default_factory=list)
    format_commands: list[str] = Field(default_factory=list)
    type_check_commands: list[str] = Field(default_factory=list)
    entrypoints: list[EntryPointCandidate]
    issues_count: int = 0
    session_id: str


class IssueRecommendation(BaseModel):
    issue_number: int
    title: str
    labels: list[str] = Field(default_factory=list)
    difficulty: str
    skill_tags: list[str]
    recommendation_reason: str
    suggested_first_steps: list[str]
    evidence: list[EvidenceItem]
    score: float
    source: str = "github_issue"
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    is_github_issue: bool = True
    why_fit_for_beginner: str = ""
    why_fit_for_this_user: str = ""
    expected_prerequisites: list[str] = Field(default_factory=list)
    task_type: str = ""
    why_this_is_a_good_first_step: str = ""
    expected_output: str = ""


class IssueRecommendationResponse(BaseModel):
    issues: list[IssueRecommendation]
    self_check: SelfCheckReport
    message: str = ""


class LearningStep(BaseModel):
    order: int
    title: str
    reason: str
    evidence: list[EvidenceItem] = Field(default_factory=list)


class LearningPathResponse(BaseModel):
    conclusion: str
    steps: list[LearningStep]
    risks: list[str]
    verifiable_commands: list[str]
    self_check: SelfCheckReport


class DevelopmentWorkflowResponse(BaseModel):
    conclusion: str
    quality_commands: list[QualityCommand] = Field(default_factory=list)
    setup_steps: list[str] = Field(default_factory=list)
    development_commands: list[QualityCommand] = Field(default_factory=list)
    test_commands: list[QualityCommand] = Field(default_factory=list)
    lint_commands: list[QualityCommand] = Field(default_factory=list)
    format_commands: list[QualityCommand] = Field(default_factory=list)
    type_check_commands: list[QualityCommand] = Field(default_factory=list)
    build_commands: list[QualityCommand] = Field(default_factory=list)
    branch_rules: list[ContributingRule] = Field(default_factory=list)
    commit_rules: list[ContributingRule] = Field(default_factory=list)
    contribution_rules: list[ContributingRule] = Field(default_factory=list)
    pull_request_rules: list[PullRequestWorkflow] = Field(default_factory=list)
    ci_rules: list[CIRule] = Field(default_factory=list)
    code_style_rules: list[ContributingRule] = Field(default_factory=list)
    setup_rules: list[ContributingRule] = Field(default_factory=list)
    test_rules: list[ContributingRule] = Field(default_factory=list)
    documentation_references: list[ContributingRule] = Field(default_factory=list)
    project_safety_policies: list[ContributingRule] = Field(default_factory=list)
    new_contributor_checklist: list[str] = Field(default_factory=list)
    evidence_docs: list[EvidenceItem] = Field(default_factory=list)
    evidence_code: list[EvidenceItem] = Field(default_factory=list)
    evidence_issues: list[EvidenceItem] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    verifiable_commands: list[str] = Field(default_factory=list)
    self_check: SelfCheckReport
    uncertainties: list[str] = Field(default_factory=list)


class LearningPathStepV2(BaseModel):
    step_id: str
    title: str
    goal: str
    why_now: str
    prerequisite_concepts: list[str] = Field(default_factory=list)
    concrete_files: list[str] = Field(default_factory=list)
    concrete_commands: list[str] = Field(default_factory=list)
    expected_observations: list[str] = Field(default_factory=list)
    worked_example: str = ""
    self_check_questions: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class LearningPathV2Response(BaseModel):
    repo_id: str
    conclusion: str
    steps: list[LearningPathStepV2] = Field(default_factory=list)
    evidence_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    hallucination_guardrails: list[str] = Field(default_factory=list)
    self_check: SelfCheckReport


class ArchitectureTour(BaseModel):
    repo_id: str
    audience: str = "newcomer"
    project_goal: str = ""
    real_world_problem: str = ""
    system_pipeline: list[str] = Field(default_factory=list)
    major_components: list[dict[str, Any]] = Field(default_factory=list)
    entry_points: list[EntryPointCandidate] = Field(default_factory=list)
    key_invariants: list[str] = Field(default_factory=list)
    critical_paths: list[dict[str, Any]] = Field(default_factory=list)
    related_docs: list[str] = Field(default_factory=list)
    related_tests: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class ModuleStudyCard(BaseModel):
    module_path: str
    role_in_system: str = ""
    why_it_exists: str = ""
    upstream_callers: list[str] = Field(default_factory=list)
    downstream_dependencies: list[str] = Field(default_factory=list)
    key_symbols: list[str] = Field(default_factory=list)
    related_tests: list[str] = Field(default_factory=list)
    related_docs: list[str] = Field(default_factory=list)
    common_change_scenarios: list[str] = Field(default_factory=list)
    risk_if_modified: list[str] = Field(default_factory=list)
    learning_order: int = 0
    audience: str = "newcomer"
    evidence: list[EvidenceItem] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class ProjectGlossaryTerm(BaseModel):
    term: str
    zh_translation: str
    category: str = "project"
    explanation: str = ""
    source_refs: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)


class ProjectGlossary(BaseModel):
    repo_id: str
    terms: list[ProjectGlossaryTerm] = Field(default_factory=list)
    translation_policy: list[str] = Field(default_factory=list)
    canonical_sources: list[str] = Field(default_factory=list)
    fidelity_warnings: list[str] = Field(default_factory=list)


class TranslationChunkRecord(BaseModel):
    chunk_id: str
    source_file: str = ""
    source_chunk_hash: str = ""
    source_commit_hash: str = ""
    source_path: str
    source_text: str
    target_lang: str = "zh-CN"
    translated_text: str = ""
    zh_text: str
    glossary_terms: list[str] = Field(default_factory=list)
    preserved_tokens: list[str] = Field(default_factory=list)
    fidelity_status: str = "deterministic_preserve_tokens"
    stale_status: str = "fresh"
    warnings: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)


class BilingualDocView(BaseModel):
    repo_id: str
    source_path: str = ""
    canonical_source: str = ""
    chunks: list[TranslationChunkRecord] = Field(default_factory=list)
    glossary: ProjectGlossary | None = None
    fidelity_warnings: list[str] = Field(default_factory=list)


class LearningCheckRequest(BaseModel):
    learner_answer: str
    topic: str = ""


class LearningCheckResponse(BaseModel):
    learner_answer: str
    grounded_feedback: str
    missing_key_points: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    mastery_estimate: str = "low"
    evidence: list[EvidenceItem] = Field(default_factory=list)


class ChangeImpactRequest(BaseModel):
    file_path: str = ""
    symbol: str = ""


class ChangeImpactResponse(BaseModel):
    query: str
    likely_affected_modules: list[str] = Field(default_factory=list)
    likely_affected_tests: list[str] = Field(default_factory=list)
    must_read_before_editing: list[str] = Field(default_factory=list)
    must_run_commands: list[str] = Field(default_factory=list)
    documentation_to_recheck: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.LOW


class OnboardingDebtReport(BaseModel):
    repo_id: str
    has_readme: bool = False
    has_architecture_doc: bool = False
    has_contributing: bool = False
    has_issue_template: bool = False
    has_pr_template: bool = False
    has_good_first_issue: bool = False
    has_skill_labels: bool = False
    has_ci: bool = False
    has_test_entry: bool = False
    has_lint_format_doc: bool = False
    has_translation_support: bool = False
    has_beginner_friendly_commands: bool = False
    onboarding_risks: list[str] = Field(default_factory=list)
    recommended_maintainer_actions: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)


class TutorialStep(BaseModel):
    title: str
    command: str = ""
    expected_output: str = ""
    related_file: str = ""
    why_matters: str = ""
    screenshot_placeholder: str = ""
    evidence: list[EvidenceItem] = Field(default_factory=list)


class TutorialDraft(BaseModel):
    tutorial_id: str
    title: str
    target_user: str = "newcomer"
    steps: list[TutorialStep] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class LearningAgentDebugBundle(BaseModel):
    repo_id: str
    learning_path_v2: LearningPathV2Response
    architecture_tour: ArchitectureTour
    module_study_cards: list[ModuleStudyCard] = Field(default_factory=list)
    glossary: ProjectGlossary
    bilingual_docs: BilingualDocView
    contribution_funnel: IssueRecommendationResponse
    onboarding_debt: OnboardingDebtReport
    tutorials: list[TutorialDraft] = Field(default_factory=list)


class RepositoryRecord(BaseModel):
    repo_id: str
    snapshot: RepoSnapshot
    graph: RepositoryIntelligenceGraph
    chunks: list[ChunkDoc] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    worker_outputs: list[WorkerOutput] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


TestWorkerInput.__test__ = False
TestWorkerResult.__test__ = False

ContributingRule.model_rebuild()
PullRequestWorkflow.model_rebuild()
CIRule.model_rebuild()
DevelopmentWorkflowGuide.model_rebuild()

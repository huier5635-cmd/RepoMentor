from app.answer.candidate_answer_generator import CandidateAnswerGenerator
from app.answer.evaluator import Evaluator
from app.answer.evidence_formatter import EvidenceFormatter
from app.core.intent_router import IntentRouter
from app.core.orchestrator import Orchestrator
from app.core.config import get_settings
from app.core.schemas import (
    AnswerBundle,
    CommandType,
    DevelopmentWorkflowWorkerInput,
    EvidenceItem,
    FileNode,
    FileType,
    QualityCommand,
    RepoSnapshot,
    RepositoryIntelligenceGraph,
    SharedWorkingMemory,
    SourceType,
    TaskType,
)
from app.data_layer.repository_intelligence_graph import RepositoryIntelligenceGraphStore
from app.services.llm_service import DeepSeekProvider, LLMService, MockProvider
from app.services.git_service import GitService
from app.services.parser_service import ParserService
from app.workers.development_workflow_worker import DevelopmentWorkflowWorker
from fastapi.testclient import TestClient


def test_intent_router_detects_setup_question():
    assert IntentRouter().classify("这个仓库怎么启动？") == TaskType.SETUP_RUN


def test_intent_router_detects_development_workflow_question():
    assert IntentRouter().classify("这个仓库如何参与贡献？PR 怎么提？") == TaskType.DEVELOPMENT_WORKFLOW


def test_graph_summary_starts_empty():
    store = RepositoryIntelligenceGraphStore()
    summary = store.summary()
    assert summary["files"] == 0
    assert summary["symbols"] == 0


def test_git_service_rejects_empty_repo_url():
    try:
        GitService().prepare_repository("")
    except ValueError as error:
        assert "non-empty" in str(error)
    else:
        raise AssertionError("empty repo_url should be rejected")


def test_parser_skips_sensitive_env_files(tmp_path):
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=secret\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("DEEPSEEK_API_KEY=\n", encoding="utf-8")
    files = ParserService().list_files(str(tmp_path))
    paths = {item.path for item in files}
    assert ".env" not in paths
    assert ".env.example" in paths


def test_settings_reads_cors_and_demo_limits(monkeypatch):
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "https://frontend.example, http://localhost:5173")
    monkeypatch.setenv("MAX_REPO_FILES", "7")
    monkeypatch.setenv("MAX_FILE_SIZE_KB", "9")
    monkeypatch.setenv("ANALYZE_TIMEOUT_SECONDS", "11")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.backend_cors_origins == ["https://frontend.example", "http://localhost:5173"]
    assert settings.max_repo_files == 7
    assert settings.max_file_size_bytes == 9 * 1024
    assert settings.analyze_timeout_seconds == 11
    get_settings.cache_clear()


def test_parser_skips_secret_and_large_files(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_REPO_FILES", "100")
    monkeypatch.setenv("MAX_FILE_SIZE_KB", "1")
    get_settings.cache_clear()
    (tmp_path / "README.md").write_text("ok", encoding="utf-8")
    (tmp_path / "secret_notes.md").write_text("do not scan", encoding="utf-8")
    (tmp_path / "large.md").write_text("x" * 2048, encoding="utf-8")
    files = ParserService().list_files(str(tmp_path))
    paths = {item.path for item in files}
    assert "README.md" in paths
    assert "secret_notes.md" not in paths
    assert "large.md" not in paths
    get_settings.cache_clear()


def test_evaluator_flags_missing_evidence():
    bundle = AnswerBundle(conclusion="这个仓库可以 npm start", verifiable_commands=["npm start"])
    report = Evaluator().evaluate(bundle, RepositoryIntelligenceGraph())
    assert report.passed is False
    assert report.missing_evidence


def test_evaluator_accepts_grounded_command():
    evidence = EvidenceItem(
        evidence_id="e1",
        source_type=SourceType.CONFIG,
        source_ref="package.json",
        quote="scripts.start",
        supports_claim="start command exists",
    )
    command = QualityCommand(
        name="start",
        command="npm start",
        command_type=CommandType.DEV,
        source_file="package.json",
        evidence_sources=["package.json"],
    )
    graph = RepositoryIntelligenceGraph(run_commands=["npm start"], quality_commands=[command])
    bundle = AnswerBundle(
        conclusion="可用 npm start 启动。",
        evidence=[evidence],
        steps=["运行 npm start"],
        verifiable_commands=["npm start"],
    )
    report = Evaluator().evaluate(bundle, graph)
    assert report.passed is True


def test_evaluator_flags_unknown_model_file_and_command():
    evidence = EvidenceItem(
        evidence_id="e1",
        source_type=SourceType.DOCS,
        source_ref="README.md",
        file_path="README.md",
        quote="Run documented command",
        supports_claim="README evidence exists",
    )
    graph = RepositoryIntelligenceGraph(files=[FileNode(path="README.md", name="README.md", file_type=FileType.DOCS)])
    bundle = AnswerBundle(
        conclusion="请运行 python scripts/missing.py 并阅读 scripts/missing.py。",
        evidence=[evidence],
        steps=["python scripts/missing.py"],
        verifiable_commands=[],
    )
    report = Evaluator().evaluate(bundle, graph)
    assert report.passed is False
    assert any("command without graph evidence" in item for item in report.hallucination_risks)
    assert any("file without graph evidence" in item for item in report.hallucination_risks)


def test_llm_provider_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    service = LLMService()
    result = service.generate("hello", prompt_type="test", evidence_count=1)
    assert isinstance(service.provider, MockProvider)
    assert result.model_info.provider == "mock"
    assert result.model_info.used_llm is False


def test_deepseek_without_key_falls_back_to_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    service = LLMService()
    result = service.generate("hello", prompt_type="test", evidence_count=1)
    assert isinstance(service.provider, DeepSeekProvider)
    assert result.model_info.provider == "deepseek"
    assert result.model_info.fallback_to_mock is True
    assert result.model_info.used_llm is False
    assert "API key" in result.model_info.error_message
    assert "secret" not in result.model_info.error_message


def test_deepseek_with_key_creates_deepseek_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")
    service = LLMService()
    assert isinstance(service.provider, DeepSeekProvider)
    assert service.provider.model == "deepseek-chat"


def test_model_status_default_deepseek_without_key_falls_back_to_mock(monkeypatch):
    monkeypatch.setattr("app.services.model_config_service.openai_sdk_available", lambda: True)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    service = LLMService()
    status = service.status()
    assert status["provider_requested"] == "deepseek"
    assert status["provider_active"] == "mock"
    assert status["fallback_to_mock"] is True
    assert status["reason"] == "missing_deepseek_api_key"
    assert status["api_key_configured"] is False
    assert status["api_key_masked"] is None


def test_model_status_deepseek_sdk_missing_falls_back_to_mock(monkeypatch):
    monkeypatch.setattr("app.services.model_config_service.openai_sdk_available", lambda: False)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")
    service = LLMService()
    status = service.status()
    assert status["provider_requested"] == "deepseek"
    assert status["provider_active"] == "mock"
    assert status["model"] == "mock-deterministic"
    assert status["requested_model"] == "deepseek-chat"
    assert status["api_key_configured"] is True
    assert status["fallback_to_mock"] is True
    assert status["reason"] == "openai_sdk_missing"
    assert status["ready"] is False


def test_model_status_deepseek_sdk_available_uses_deepseek_model(monkeypatch):
    monkeypatch.setattr("app.services.model_config_service.openai_sdk_available", lambda: True)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")
    service = LLMService()
    status = service.status()
    assert status["provider_requested"] == "deepseek"
    assert status["provider_active"] == "deepseek"
    assert status["model"] == "deepseek-chat"
    assert status["fallback_to_mock"] is False


def test_model_status_deepseek_never_uses_mock_model_name(monkeypatch):
    monkeypatch.setattr("app.services.model_config_service.openai_sdk_available", lambda: True)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "mock-deterministic")
    service = LLMService()
    status = service.status()
    assert status["provider_active"] == "deepseek"
    assert status["requested_model"] == "deepseek-chat"
    assert status["model"] == "deepseek-chat"
    assert service.provider.model == "deepseek-chat"


def test_model_test_sdk_missing_returns_clear_error_without_500(monkeypatch):
    monkeypatch.setattr("app.services.model_config_service.openai_sdk_available", lambda: False)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-test-key")
    service = LLMService()
    result = service.test_connection()
    assert result["success"] is False
    assert result["provider_requested"] == "deepseek"
    assert result["provider_active"] == "mock"
    assert result["fallback_to_mock"] is True
    assert result["reason"] == "openai_sdk_missing"
    assert result["error"] == "openai SDK is not installed or importable. Run pip install openai."


def test_model_test_endpoint_sdk_missing_returns_clear_error(monkeypatch):
    monkeypatch.setattr("app.services.model_config_service.openai_sdk_available", lambda: False)
    from app.api import model as model_api
    from app.main import app

    monkeypatch.setattr(model_api, "orchestrator", Orchestrator())
    client = TestClient(app)
    config_response = client.post(
        "/api/model/config",
        json={
            "provider": "deepseek",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com",
            "api_key": "secret-test-key",
            "persist": False,
        },
    )
    assert config_response.status_code == 200
    response = client.post("/api/model/test")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["provider_active"] == "mock"
    assert payload["reason"] == "openai_sdk_missing"
    assert payload["error"] == "openai SDK is not installed or importable. Run pip install openai."


def test_model_test_deepseek_success_uses_openai_compatible_defaults(monkeypatch):
    monkeypatch.setattr("app.services.model_config_service.openai_sdk_available", lambda: True)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    calls = {}

    def fake_generate(self, prompt, system=None, **kwargs):
        calls["prompt"] = prompt
        calls["system"] = system
        calls["model"] = self.model
        calls["base_url"] = self.base_url
        return "OK"

    monkeypatch.setattr(DeepSeekProvider, "generate", fake_generate)
    service = LLMService()
    result = service.test_connection()
    assert result["success"] is True
    assert result["provider_active"] == "deepseek"
    assert result["model"] == "deepseek-chat"
    assert result["fallback_to_mock"] is False
    assert calls == {
        "prompt": "只回复 OK",
        "system": "You are a connection test.",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
    }


def test_runtime_configure_deepseek_status_redacts_key(monkeypatch):
    monkeypatch.setattr("app.services.model_config_service.openai_sdk_available", lambda: True)
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    service = LLMService()
    status = service.configure(
        "deepseek",
        deepseek_api_key="secret-runtime-key",
        deepseek_model="deepseek-chat",
        deepseek_base_url="https://api.deepseek.com",
    )
    dumped = str(status)
    assert status["provider"] == "deepseek"
    assert status["provider_requested"] == "deepseek"
    assert status["provider_active"] == "deepseek"
    assert status["api_key_configured"] is True
    assert status["api_key_masked"].startswith("sec")
    assert status["has_api_key"] is True
    assert status["ready"] is True
    assert "secret-runtime-key" not in dumped


def test_runtime_configure_deepseek_can_switch_model_without_reentering_key(monkeypatch):
    monkeypatch.setattr("app.services.model_config_service.openai_sdk_available", lambda: True)
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    service = LLMService()
    service.configure(
        "deepseek",
        deepseek_api_key="secret-runtime-key",
        deepseek_model="deepseek-chat",
        deepseek_base_url="https://api.deepseek.com",
    )
    status = service.configure(
        "deepseek",
        deepseek_api_key="",
        deepseek_model="deepseek-reasoner",
        deepseek_base_url="https://api.deepseek.com",
    )
    assert status["provider"] == "deepseek"
    assert status["model"] == "deepseek-reasoner"
    assert status["has_api_key"] is True
    assert status["ready"] is True


def test_orchestrator_model_config_masks_key_and_status_uses_runtime_config(monkeypatch):
    monkeypatch.setattr("app.services.model_config_service.openai_sdk_available", lambda: True)
    orchestrator = Orchestrator()
    secret = "secret-api-key-for-test"
    payload = orchestrator.configure_model(
        {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com",
            "api_key": secret,
            "persist": False,
        }
    )
    dumped = str(payload)
    assert payload["provider_requested"] == "deepseek"
    assert payload["provider_active"] == "deepseek"
    assert payload["api_key_configured"] is True
    assert payload["api_key_masked"].endswith("test")
    assert secret not in dumped

    status = orchestrator.get_model_status()
    assert status["api_key_configured"] is True
    assert secret not in str(status)
    orchestrator.configure_model({"provider": "mock", "persist": False})


def test_repoqa_skips_llm_when_evidence_empty(monkeypatch):
    orchestrator = Orchestrator()
    calls = {"count": 0}

    def fake_generate(*args, **kwargs):
        calls["count"] += 1
        raise AssertionError("LLM should not be called without evidence")

    monkeypatch.setattr(orchestrator.llm_service, "generate", fake_generate)
    memory = orchestrator.memory_store.start_session("r1", "这个项目怎么启动？")
    bundle = AnswerBundle(conclusion="当前证据不足", evidence=[], confidence=0.2)
    result = orchestrator._maybe_generate_llm_answer(
        TaskType.SETUP_RUN,
        "这个项目怎么启动？",
        memory,
        RepositoryIntelligenceGraph(),
        bundle,
    )
    assert calls["count"] == 0
    assert result.model_info.used_llm is False
    assert result.model_info.prompt_type == "not_called"


def test_repoqa_calls_llm_when_evidence_exists(monkeypatch):
    orchestrator = Orchestrator()
    evidence = EvidenceItem(
        evidence_id="e1",
        source_type=SourceType.DOCS,
        source_ref="README.md",
        file_path="README.md",
        quote="python scripts/run_demo.py",
        supports_claim="README documents run command",
    )
    command = QualityCommand(
        name="demo",
        command="python scripts/run_demo.py",
        command_type=CommandType.DEV,
        source_file="README.md",
        evidence_sources=["README.md"],
    )
    graph = RepositoryIntelligenceGraph(
        files=[FileNode(path="README.md", name="README.md", file_type=FileType.DOCS)],
        run_commands=["python scripts/run_demo.py"],
        quality_commands=[command],
    )
    memory = orchestrator.memory_store.start_session("r1", "这个项目怎么启动？")
    bundle = AnswerBundle(
        conclusion="先运行 demo。",
        evidence=[evidence],
        steps=["python scripts/run_demo.py"],
        verifiable_commands=["python scripts/run_demo.py"],
        confidence=0.8,
    )

    class FakeLLM:
        provider_name = "deepseek"

        def generate(self, *args, **kwargs):
            from app.core.schemas import ModelInfo
            from app.services.llm_service import LLMServiceResult

            return LLMServiceResult(
                text='{"conclusion":"推荐运行 demo。","steps":["1. 推荐启动方式：python scripts/run_demo.py"],"risks":[],"verifiable_commands":["python scripts/run_demo.py"],"uncertainties":[]}',
                model_info=ModelInfo(provider="deepseek", model="deepseek-chat", prompt_type="setup_run", evidence_count=1, used_llm=True),
            )

    orchestrator.llm_service = FakeLLM()
    result = orchestrator._maybe_generate_llm_answer(TaskType.SETUP_RUN, "这个项目怎么启动？", memory, graph, bundle)
    assert result.conclusion == "推荐运行 demo。"
    assert result.model_info.used_llm is True


def test_setup_run_answer_outputs_concrete_commands():
    evidence = EvidenceItem(
        evidence_id="e1",
        source_type=SourceType.DOCS,
        source_ref="README.md",
        file_path="README.md",
        quote="pip install -r requirements.txt\npython scripts/run_demo.py\npython -m pytest tests",
        supports_claim="README documents setup commands",
    )
    graph = RepositoryIntelligenceGraph(
        setup_commands=["pip install -r requirements.txt"],
        run_commands=["python scripts/run_demo.py"],
        test_commands=["python -m pytest tests"],
        quality_commands=[
            QualityCommand(name="install", command="pip install -r requirements.txt", command_type=CommandType.SETUP, source_file="README.md", evidence_sources=["README.md"]),
            QualityCommand(name="demo", command="python scripts/run_demo.py", command_type=CommandType.DEV, source_file="README.md", evidence_sources=["README.md"]),
            QualityCommand(name="test", command="python -m pytest tests", command_type=CommandType.TEST, source_file="README.md", evidence_sources=["README.md"]),
        ],
    )
    memory = SharedWorkingMemory(session_id="s1", current_task="setup_run", user_question="这个项目怎么启动？", retrieved_evidence=[evidence])
    answer = CandidateAnswerGenerator().generate(TaskType.SETUP_RUN, memory, graph)
    assert "pip install -r requirements.txt" in answer.verifiable_commands
    assert "python scripts/run_demo.py" in answer.verifiable_commands
    assert "python -m pytest tests" in answer.verifiable_commands


def test_final_answer_json_contains_model_info():
    bundle = AnswerBundle(conclusion="ok")
    self_check = Evaluator().evaluate(bundle, RepositoryIntelligenceGraph())
    answer = EvidenceFormatter().format(bundle, self_check, ["trace"])
    dumped = answer.model_dump(mode="json")
    assert "model_info" in dumped
    assert dumped["model_info"]["provider"] == "mock"


def test_development_workflow_worker_extracts_commands(tmp_path):
    (tmp_path / "README.md").write_text("## Contribute\nRun tests:\npytest\nRun lint:\nruff check .\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n[tool.ruff]\n", encoding="utf-8")
    files = [
        FileNode(
            path="README.md",
            name="README.md",
            extension=".md",
            language="markdown",
            file_type=FileType.DOCS,
            size=50,
            content_preview="Run tests: pytest",
            line_count=4,
        ),
        FileNode(
            path="pyproject.toml",
            name="pyproject.toml",
            extension=".toml",
            language="toml",
            file_type=FileType.CONFIG,
            size=30,
            content_preview="[tool.ruff]",
            line_count=2,
        ),
    ]
    snapshot = RepoSnapshot(repo_id="r1", repo_url=str(tmp_path), local_path=str(tmp_path), files=files)
    graph = RepositoryIntelligenceGraph(files=files)
    result = DevelopmentWorkflowWorker().run(DevelopmentWorkflowWorkerInput(repo_snapshot=snapshot, graph=graph))
    assert result.guide.test_commands
    assert result.guide.lint_commands

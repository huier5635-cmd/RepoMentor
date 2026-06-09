from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.schemas import ModelInfo
from app.services.model_config_service import DEFAULT_DEEPSEEK_MODEL, ModelConfigService, normalize_deepseek_model

logger = logging.getLogger(__name__)

OPENAI_SDK_INSTALL_MESSAGE = "openai SDK is not installed. Please run: pip install openai"
OPENAI_SDK_TEST_ERROR = "openai SDK is not installed or importable. Run pip install openai."

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except Exception:
    # Loading .env is a convenience for local development. Environment
    # variables supplied by the process still work without python-dotenv.
    pass


@dataclass
class LLMServiceResult:
    text: str
    model_info: ModelInfo


class BaseLLMProvider:
    provider_name = "base"
    model = "unknown"
    uses_external_llm = False

    def generate(self, prompt: str, system: str | None = None, **kwargs) -> str:
        raise NotImplementedError


class MockProvider(BaseLLMProvider):
    provider_name = "mock"
    model = "mock-deterministic"
    uses_external_llm = False

    def generate(self, prompt: str, system: str | None = None, **kwargs) -> str:
        return (
            '{"conclusion":"Mock provider: deterministic evidence-grounded answer.",'
            '"steps":["基于已检索 evidence 生成确定性 mock 回答。"],'
            '"risks":["Mock 模式不会调用真实模型。"],'
            '"verifiable_commands":[],"uncertainties":[]}'
        )


class DeepSeekProvider(BaseLLMProvider):
    provider_name = "deepseek"
    uses_external_llm = True

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("DEEPSEEK_API_KEY", "")).strip()
        self.model = normalize_deepseek_model(model or os.getenv("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL))
        self.base_url = (base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")).strip() or "https://api.deepseek.com"
        self.temperature = temperature if temperature is not None else _float_env("LLM_TEMPERATURE", 0.2)
        self.max_tokens = max_tokens if max_tokens is not None else _int_env("LLM_MAX_TOKENS", 1200)

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system: str | None = None, **kwargs) -> str:
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not set")
        try:
            from openai import OpenAI
        except Exception as error:
            raise RuntimeError(OPENAI_SDK_INSTALL_MESSAGE) from error

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system or ""},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""


class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"
    uses_external_llm = True

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "")).strip()
        self.model = (model or os.getenv("OPENAI_MODEL", "")).strip() or "gpt-4o-mini"
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).strip() or "https://api.openai.com/v1"
        self.temperature = temperature if temperature is not None else _float_env("LLM_TEMPERATURE", 0.2)
        self.max_tokens = max_tokens if max_tokens is not None else _int_env("LLM_MAX_TOKENS", 1200)

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system: str | None = None, **kwargs) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        try:
            from openai import OpenAI
        except Exception as error:
            raise RuntimeError(OPENAI_SDK_INSTALL_MESSAGE) from error

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system or ""},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""


class LLMService:
    def __init__(self) -> None:
        self.model_config_service = ModelConfigService()
        self.provider_name = self.model_config_service.get_model_config().provider
        self.mock_provider = MockProvider()
        self.provider = self._select_provider(self.provider_name)
        self.call_log: list[ModelInfo] = []

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        prompt_type: str = "general",
        evidence_count: int = 0,
    ) -> LLMServiceResult:
        started = time.perf_counter()
        fallback_to_mock = False
        error_message = ""
        provider = self.provider

        if isinstance(provider, (DeepSeekProvider, OpenAIProvider)) and not provider.available:
            fallback_to_mock = True
            error_message = f"{provider.provider_name.upper()} API key is not set; using MockProvider"
            logger.warning("LLM provider %s has no API key; falling back to mock", provider.provider_name)
            provider = self.mock_provider

        try:
            text = provider.generate(prompt, system=system)
            success = True
        except Exception as error:
            fallback_to_mock = True
            error_message = self._sanitize_error(str(error))
            logger.warning("LLM provider %s failed; falling back to mock: %s", self.provider_name, error_message)
            provider = self.mock_provider
            text = provider.generate(prompt, system=system)
            success = False

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        model_info = ModelInfo(
            provider=self.provider_name,
            model=getattr(provider, "model", "mock-deterministic"),
            prompt_type=prompt_type,
            evidence_count=evidence_count,
            elapsed_ms=elapsed_ms,
            success=success,
            used_llm=getattr(provider, "uses_external_llm", False) and not fallback_to_mock and success,
            fallback_to_mock=fallback_to_mock,
            error_message=error_message,
        )
        self.call_log.append(model_info)
        logger.info(
            "llm_call provider=%s model=%s prompt_type=%s evidence_count=%s success=%s fallback_to_mock=%s elapsed_ms=%s",
            model_info.provider,
            model_info.model,
            model_info.prompt_type,
            model_info.evidence_count,
            model_info.success,
            model_info.fallback_to_mock,
            model_info.elapsed_ms,
        )
        return LLMServiceResult(text=text, model_info=model_info)

    def summarize(self, prompt: str) -> str:
        return self.generate(prompt, prompt_type="summary", evidence_count=1).text

    def configure(
        self,
        provider_name: str,
        *,
        deepseek_api_key: str = "",
        deepseek_model: str = "deepseek-chat",
        deepseek_base_url: str = "https://api.deepseek.com",
        openai_api_key: str = "",
        openai_model: str = "",
        openai_base_url: str = "https://api.openai.com/v1",
    ) -> dict[str, object]:
        provider_name = (provider_name or "mock").strip().lower()
        if provider_name == "deepseek":
            self.configure_model(
                provider="deepseek",
                model=deepseek_model,
                base_url=deepseek_base_url,
                api_key=deepseek_api_key,
                persist=False,
            )
        elif provider_name == "openai":
            self.configure_model(
                provider="openai",
                model=openai_model,
                base_url=openai_base_url,
                api_key=openai_api_key,
                persist=False,
            )
        else:
            self.configure_model(provider="mock", persist=False)
        return self.status()

    def configure_model(
        self,
        *,
        provider: str,
        model: str = "",
        base_url: str = "",
        api_key: str = "",
        persist: bool = False,
    ) -> dict[str, object]:
        self.model_config_service.update_runtime_model_config(
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            persist=persist,
        )
        config = self.model_config_service.get_model_config()
        self.provider_name = config.provider
        self.provider = self._select_provider(self.provider_name)
        status = self.status()
        logger.info(
            "model_configured provider_requested=%s provider_active=%s model=%s api_key_configured=%s persist=%s",
            status["provider_requested"],
            status["provider_active"],
            status["model"],
            status["api_key_configured"],
            persist,
        )
        return status

    def status(self) -> dict[str, object]:
        last_call = self.call_log[-1].model_dump(mode="json") if self.call_log else None
        return self.model_config_service.get_model_status(last_call=last_call)

    def test_connection(self) -> dict[str, object]:
        status = self.status()
        if status["provider_active"] == "mock":
            if status.get("reason") == "openai_sdk_missing":
                return {
                    "success": False,
                    "provider_requested": status["provider_requested"],
                    "provider_active": "mock",
                    "model": "mock-deterministic",
                    "fallback_to_mock": True,
                    "reason": "openai_sdk_missing",
                    "error": OPENAI_SDK_TEST_ERROR,
                    "error_message": OPENAI_SDK_TEST_ERROR,
                }
            if status["fallback_to_mock"]:
                return {
                    "success": False,
                    "provider_requested": status["provider_requested"],
                    "provider_active": "mock",
                    "model": "mock-deterministic",
                    "fallback_to_mock": True,
                    "reason": status["reason"],
                    "error": "API key is not configured; current provider is falling back to MockProvider.",
                    "error_message": "API key is not configured; current provider is falling back to MockProvider.",
                }
            return {
                "success": True,
                "provider_requested": "mock",
                "provider_active": "mock",
                "model": "mock-deterministic",
                "fallback_to_mock": False,
                "message": "MockProvider is available.",
            }
        try:
            requested = str(status["provider_requested"])
            if requested == "deepseek":
                config = self.model_config_service.get_model_config()
                provider = DeepSeekProvider(
                    api_key=config.deepseek_api_key,
                    model="deepseek-chat",
                    base_url="https://api.deepseek.com",
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                )
            else:
                provider = self._select_provider(requested)
            started = time.perf_counter()
            provider.generate("只回复 OK", system="You are a connection test.")
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            model = getattr(provider, "model", str(status["model"]))
            return {
                "success": True,
                "provider_requested": requested,
                "provider_active": requested,
                "model": model,
                "fallback_to_mock": False,
                "elapsed_ms": elapsed_ms,
            }
        except Exception as error:
            error_message = self._sanitize_error(str(error))
            sdk_missing = "openai SDK" in error_message
            if sdk_missing:
                error_message = OPENAI_SDK_TEST_ERROR
            return {
                "success": False,
                "provider_requested": status["provider_requested"],
                "provider_active": "mock" if sdk_missing else status["provider_active"],
                "model": "mock-deterministic" if sdk_missing else status["model"],
                "fallback_to_mock": sdk_missing,
                "reason": "openai_sdk_missing" if sdk_missing else None,
                "error": error_message,
                "error_message": error_message,
            }

    def _select_provider(self, provider_name: str) -> BaseLLMProvider:
        config = self.model_config_service.get_model_config()
        if provider_name == "deepseek":
            return DeepSeekProvider(
                api_key=config.deepseek_api_key,
                model=config.deepseek_model,
                base_url=config.deepseek_base_url,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
        if provider_name == "openai":
            return OpenAIProvider(
                api_key=config.openai_api_key,
                model=config.openai_model,
                base_url=config.openai_base_url,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
        if provider_name != "mock":
            logger.warning("Unknown LLM_PROVIDER=%s; falling back to mock", provider_name)
        return self.mock_provider

    def _sanitize_error(self, message: str) -> str:
        secrets = [
            getattr(self.provider, "api_key", ""),
            getattr(self.mock_provider, "api_key", ""),
        ]
        sanitized = message
        for secret in secrets:
            if secret:
                sanitized = sanitized.replace(secret, "[redacted]")
        return sanitized


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default

from __future__ import annotations

import os
from importlib import import_module
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROVIDERS = {"mock", "deepseek", "openai"}
MOCK_MODEL = "mock-deterministic"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
ENV_KEYS = [
    "GITHUB_TOKEN",
    "LLM_PROVIDER",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_MODEL",
    "DEEPSEEK_BASE_URL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_BASE_URL",
    "LLM_TEMPERATURE",
    "LLM_MAX_TOKENS",
]


def openai_sdk_available() -> bool:
    try:
        module = import_module("openai")
        getattr(module, "OpenAI")
    except Exception:
        return False
    return True


def normalize_deepseek_model(model: str | None) -> str:
    value = (model or "").strip()
    if not value or value == MOCK_MODEL:
        return DEFAULT_DEEPSEEK_MODEL
    return value


@dataclass(frozen=True)
class ModelRuntimeConfig:
    provider: str = "deepseek"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"
    openai_api_key: str = ""
    openai_model: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    temperature: float = 0.2
    max_tokens: int = 1200


class ModelConfigService:
    def __init__(self, env_path: Path | None = None) -> None:
        self.backend_dir = Path(__file__).resolve().parents[2]
        self.repo_dir = self.backend_dir.parent
        self.env_path = env_path or self.backend_dir / ".env"
        self.runtime: dict[str, str] = {}

    def get_model_config(self) -> ModelRuntimeConfig:
        provider = self._value("LLM_PROVIDER", "deepseek").strip().lower() or "deepseek"
        if provider not in PROVIDERS:
            provider = "mock"
        return ModelRuntimeConfig(
            provider=provider,
            deepseek_api_key=self._value("DEEPSEEK_API_KEY", ""),
            deepseek_model=normalize_deepseek_model(self._value("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL)),
            deepseek_base_url=self._value("DEEPSEEK_BASE_URL", "https://api.deepseek.com") or "https://api.deepseek.com",
            openai_api_key=self._value("OPENAI_API_KEY", ""),
            openai_model=self._value("OPENAI_MODEL", ""),
            openai_base_url=self._value("OPENAI_BASE_URL", "https://api.openai.com/v1") or "https://api.openai.com/v1",
            temperature=self._float_value("LLM_TEMPERATURE", 0.2),
            max_tokens=self._int_value("LLM_MAX_TOKENS", 1200),
        )

    def update_runtime_model_config(
        self,
        *,
        provider: str,
        model: str = "",
        base_url: str = "",
        api_key: str = "",
        persist: bool = False,
    ) -> dict[str, Any]:
        provider = (provider or "mock").strip().lower()
        if provider not in PROVIDERS:
            provider = "mock"

        current = self.get_model_config()
        self.runtime["LLM_PROVIDER"] = provider
        if provider == "deepseek":
            self.runtime["DEEPSEEK_API_KEY"] = api_key.strip() or current.deepseek_api_key
            self.runtime["DEEPSEEK_MODEL"] = normalize_deepseek_model(model.strip() or current.deepseek_model)
            self.runtime["DEEPSEEK_BASE_URL"] = base_url.strip() or current.deepseek_base_url or "https://api.deepseek.com"
        elif provider == "openai":
            self.runtime["OPENAI_API_KEY"] = api_key.strip() or current.openai_api_key
            self.runtime["OPENAI_MODEL"] = model.strip() or current.openai_model or "gpt-4o-mini"
            self.runtime["OPENAI_BASE_URL"] = base_url.strip() or current.openai_base_url or "https://api.openai.com/v1"

        if persist:
            self.write_env_if_persist_enabled()
        return self.get_model_status()

    def get_model_status(self, last_call: dict[str, Any] | None = None) -> dict[str, Any]:
        config = self.get_model_config()
        requested = config.provider
        api_key = ""
        base_url: str | None = None
        requested_model = "mock-deterministic"
        reason: str | None = None
        requires_openai_sdk = requested in {"deepseek", "openai"}
        sdk_available = True

        if requested == "deepseek":
            api_key = config.deepseek_api_key
            base_url = config.deepseek_base_url
            requested_model = config.deepseek_model
            sdk_available = openai_sdk_available()
            if not sdk_available:
                reason = "openai_sdk_missing"
            elif not api_key:
                reason = "missing_deepseek_api_key"
        elif requested == "openai":
            api_key = config.openai_api_key
            base_url = config.openai_base_url
            requested_model = config.openai_model or "gpt-4o-mini"
            sdk_available = openai_sdk_available()
            if not sdk_available:
                reason = "openai_sdk_missing"
            elif not api_key:
                reason = "missing_openai_api_key"

        if requested == "mock":
            active = "mock"
            model = "mock-deterministic"
            active_base_url = None
            fallback_to_mock = False
        elif api_key and sdk_available:
            active = requested
            model = requested_model
            active_base_url = base_url
            fallback_to_mock = False
        else:
            active = "mock"
            model = "mock-deterministic"
            active_base_url = None
            fallback_to_mock = True

        status = {
            "provider_requested": requested,
            "provider_active": active,
            "model": model,
            "requested_model": requested_model,
            "base_url": active_base_url,
            "api_key_configured": bool(api_key),
            "api_key_masked": self.mask_api_key(api_key) if api_key else None,
            "fallback_to_mock": fallback_to_mock,
            "reason": reason if fallback_to_mock else None,
            "openai_sdk_available": sdk_available,
            "last_call": last_call,
        }
        status.update(
            {
                "provider": requested,
                "has_api_key": bool(api_key),
                "uses_external_llm": active != "mock",
                "ready": requested == "mock" or (bool(api_key) and (not requires_openai_sdk or sdk_available)),
            }
        )
        return status

    def mask_api_key(self, api_key: str) -> str:
        key = (api_key or "").strip()
        if not key:
            return ""
        if len(key) <= 8:
            return f"{key[:2]}-****"
        return f"{key[:3]}****{key[-4:]}"

    def write_env_if_persist_enabled(self) -> None:
        self._ensure_env_is_gitignored()
        config = self.get_model_config()
        values = {
            "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", ""),
            "LLM_PROVIDER": config.provider,
            "DEEPSEEK_API_KEY": config.deepseek_api_key,
            "DEEPSEEK_MODEL": config.deepseek_model,
            "DEEPSEEK_BASE_URL": config.deepseek_base_url,
            "OPENAI_API_KEY": config.openai_api_key,
            "OPENAI_MODEL": config.openai_model,
            "OPENAI_BASE_URL": config.openai_base_url,
            "LLM_TEMPERATURE": str(config.temperature),
            "LLM_MAX_TOKENS": str(config.max_tokens),
        }
        existing = self._read_env_lines()
        seen: set[str] = set()
        next_lines: list[str] = []
        for line in existing:
            key = line.split("=", 1)[0].strip() if "=" in line else ""
            if key in values:
                next_lines.append(f"{key}={values[key]}")
                seen.add(key)
            else:
                next_lines.append(line)
        for key in ENV_KEYS:
            if key not in seen:
                next_lines.append(f"{key}={values.get(key, '')}")
        self.env_path.write_text("\n".join(next_lines).rstrip() + "\n", encoding="utf-8")

    def _read_env_lines(self) -> list[str]:
        if not self.env_path.exists():
            return []
        return self.env_path.read_text(encoding="utf-8").splitlines()

    def _ensure_env_is_gitignored(self) -> None:
        gitignore = self.repo_dir / ".gitignore"
        if not gitignore.exists():
            raise RuntimeError("Cannot persist model config because .gitignore is missing")
        entries = {
            line.strip().replace("\\", "/")
            for line in gitignore.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        if ".env" not in entries and "backend/.env" not in entries:
            raise RuntimeError("Cannot persist model config because backend/.env is not gitignored")

    def _value(self, name: str, default: str) -> str:
        return self.runtime.get(name) or os.getenv(name, default)

    def _float_value(self, name: str, default: float) -> float:
        try:
            return float(self._value(name, str(default)))
        except ValueError:
            return default

    def _int_value(self, name: str, default: int) -> int:
        try:
            return int(self._value(name, str(default)))
        except ValueError:
            return default

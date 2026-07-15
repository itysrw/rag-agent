"""Application settings loaded independently of the current directory."""

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Settings required by the Day 2 API process."""

    name: str = "Enterprise Knowledge Base RAG Agent"
    version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        extra="ignore",
    )


class LLMSettings(BaseSettings):
    """OpenAI-compatible language model connection settings."""

    api_key: SecretStr | None = None
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    timeout_seconds: float = Field(default=60.0, gt=0)
    extra_body: dict[str, Any] = Field(
        default_factory=lambda: {"thinking": {"type": "disabled"}}
    )

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="LLM_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()


@lru_cache
def get_llm_settings() -> LLMSettings:
    """Return cached OpenAI-compatible language model settings."""
    return LLMSettings()

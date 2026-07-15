"""Application settings loaded independently of the current directory."""

from functools import lru_cache
from pathlib import Path
from typing import Any, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MAX_UPLOAD_SIZE = 20 * 1024 * 1024
MAX_PDF_PAGES = 500
READ_CHUNK_SIZE = 1024 * 1024


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


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection settings without an embedded credential."""

    host: str = "localhost"
    port: int = Field(default=5432, ge=1, le=65535)
    db: str = "ragagent"
    user: str = "postgres"
    password: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="POSTGRES_",
        extra="ignore",
    )


class DocumentSettings(BaseSettings):
    """Document storage and parser resource limits."""

    upload_dir: Path = PROJECT_ROOT / "data" / "uploads"
    max_upload_size: int = Field(default=MAX_UPLOAD_SIZE, gt=0)
    max_pdf_pages: int = Field(default=MAX_PDF_PAGES, gt=0)
    read_chunk_size: int = Field(default=READ_CHUNK_SIZE, gt=0)

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("upload_dir", mode="after")
    @classmethod
    def resolve_upload_dir(cls, value: Path) -> Path:
        """Resolve relative upload paths from the repository root."""
        if value.is_absolute():
            return value.resolve()
        return (PROJECT_ROOT / value).resolve()


class ChunkingSettings(BaseSettings):
    """Token-based text chunking settings for newly uploaded documents."""

    chunk_size: int = Field(default=500, gt=0)
    chunk_overlap: int = Field(default=100, ge=0)
    chunk_encoding_name: str = "o200k_base"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )

    @field_validator("chunk_encoding_name")
    @classmethod
    def validate_encoding_name(cls, value: str) -> str:
        """Reject an empty tokenizer encoding name."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("chunk_encoding_name must not be empty")
        return normalized

    @model_validator(mode="after")
    def validate_overlap(self) -> Self:
        """Require overlap to be strictly smaller than the chunk size."""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()


@lru_cache
def get_llm_settings() -> LLMSettings:
    """Return cached OpenAI-compatible language model settings."""
    return LLMSettings()


@lru_cache
def get_database_settings() -> DatabaseSettings:
    """Return cached PostgreSQL connection settings."""
    return DatabaseSettings()


@lru_cache
def get_document_settings() -> DocumentSettings:
    """Return cached document storage and parser settings."""
    return DocumentSettings()


@lru_cache
def get_chunking_settings() -> ChunkingSettings:
    """Return cached token-based text chunking settings."""
    return ChunkingSettings()

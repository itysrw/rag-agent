"""Application settings loaded independently of the current directory."""

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MAX_UPLOAD_SIZE = 20 * 1024 * 1024
MAX_PDF_PAGES = 500
READ_CHUNK_SIZE = 1024 * 1024
EMBEDDING_MODEL_NAME = "BAAI/bge-small-zh-v1.5"
EMBEDDING_MODEL_REVISION = "4bf3c54884c552e68da7eb27f3e9bdc5a32e32d4"
EMBEDDING_DIMENSION = 512
EMBEDDING_MAX_BATCH_SIZE = 32
QDRANT_MAX_BATCH_SIZE = 32
RAG_MIN_RELEVANCE_SCORE = 0.46


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


class EmbeddingSettings(BaseSettings):
    """Pinned local BGE document-embedding settings for Day 6."""

    model_name: Literal["BAAI/bge-small-zh-v1.5"] = EMBEDDING_MODEL_NAME
    model_revision: Literal[
        "4bf3c54884c552e68da7eb27f3e9bdc5a32e32d4"
    ] = EMBEDDING_MODEL_REVISION
    dimension: Literal[512] = EMBEDDING_DIMENSION
    batch_size: int = Field(default=EMBEDDING_MAX_BATCH_SIZE, gt=0, le=32)
    device: Literal["cpu"] = "cpu"
    normalize_embeddings: bool = Field(
        default=True,
        validation_alias="EMBEDDING_NORMALIZE",
    )
    cache_dir: Path = PROJECT_ROOT / "data" / "models"
    download_max_retries: int = Field(default=3, ge=0, le=3)
    retry_base_delay_seconds: float = Field(default=1.0, gt=0)

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="EMBEDDING_",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("cache_dir", mode="after")
    @classmethod
    def resolve_cache_dir(cls, value: Path) -> Path:
        """Resolve relative model cache paths from the repository root."""
        if value.is_absolute():
            return value.resolve()
        return (PROJECT_ROOT / value).resolve()

    @field_validator("normalize_embeddings")
    @classmethod
    def require_normalized_vectors(cls, value: bool) -> bool:
        """Keep vector normalization mandatory for the Day 6 contract."""
        if not value:
            raise ValueError("normalize_embeddings must remain enabled")
        return value


class QdrantSettings(BaseSettings):
    """Local Qdrant connection and write limits for Day 7."""

    host: str = "localhost"
    port: int = Field(default=6333, ge=1, le=65535)
    collection: str = "documents"
    timeout_seconds: float = Field(default=10.0, gt=0)
    upsert_batch_size: int = Field(
        default=QDRANT_MAX_BATCH_SIZE,
        gt=0,
        le=QDRANT_MAX_BATCH_SIZE,
    )

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="QDRANT_",
        extra="ignore",
    )

    @field_validator("host", "collection")
    @classmethod
    def strip_nonempty_value(cls, value: str) -> str:
        """Normalize required Qdrant text settings."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Qdrant text settings must not be empty")
        return normalized

    def build_url(self) -> str:
        """Build the local REST endpoint without credentials."""
        return f"http://{self.host}:{self.port}"


class RAGSettings(BaseSettings):
    """Generation-layer relevance gate for the Day 8 RAG flow."""

    min_relevance_score: float = Field(
        default=RAG_MIN_RELEVANCE_SCORE,
        ge=0.0,
        le=1.0,
    )

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="RAG_",
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


@lru_cache
def get_embedding_settings() -> EmbeddingSettings:
    """Return cached local BGE document-embedding settings."""
    return EmbeddingSettings()


@lru_cache
def get_qdrant_settings() -> QdrantSettings:
    """Return cached local Qdrant settings."""
    return QdrantSettings()


@lru_cache
def get_rag_settings() -> RAGSettings:
    """Return cached Day 8 RAG relevance settings."""
    return RAGSettings()

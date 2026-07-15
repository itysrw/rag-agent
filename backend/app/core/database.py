"""Lazy PostgreSQL engine and session construction."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, URL, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.core.config import DatabaseSettings, get_database_settings


class Base(DeclarativeBase):
    """Base class for relational models."""


class DatabaseConfigurationError(RuntimeError):
    """Raised when PostgreSQL credentials are not configured."""


def build_database_url(settings: DatabaseSettings) -> URL:
    """Build a password-safe SQLAlchemy URL for PostgreSQL."""
    if settings.password is None:
        raise DatabaseConfigurationError("POSTGRES_PASSWORD is not configured")

    password = settings.password.get_secret_value().strip()
    if not password or password == "your_postgres_password_here":
        raise DatabaseConfigurationError("POSTGRES_PASSWORD is not configured")

    return URL.create(
        drivername="postgresql+psycopg",
        username=settings.user,
        password=password,
        host=settings.host,
        port=settings.port,
        database=settings.db,
    )


@lru_cache
def get_engine() -> Engine:
    """Return a cached engine without opening a startup connection."""
    return create_engine(
        build_database_url(get_database_settings()),
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return the cached synchronous SQLAlchemy session factory."""
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_database_session() -> Iterator[Session]:
    """Yield one request-scoped database session."""
    with get_session_factory()() as session:
        yield session

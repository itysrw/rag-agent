"""FastAPI application assembly."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from loguru import logger
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from backend.app.api.chat import router as chat_router
from backend.app.api.documents import router as documents_router
from backend.app.api.health import router as health_router
from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.debug)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Log application startup and shutdown events."""
    logger.info("Application starting")
    try:
        yield
    finally:
        logger.info("Application shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title=settings.name,
        version=settings.version,
        lifespan=lifespan,
    )

    application.include_router(health_router)
    application.include_router(chat_router)
    application.include_router(documents_router)

    @application.middleware("http")
    async def log_request(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        started_at = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("{} {} failed", request.method, request.url.path)
            raise

        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.info(
            "{} {} -> {} ({:.2f} ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    return application


app = create_app()

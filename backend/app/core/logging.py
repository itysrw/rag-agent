"""Central Loguru configuration."""

import sys
from typing import Any

from loguru import logger

JSONL_LOG_MARKER = "jsonl"


def configure_logging(debug: bool) -> None:
    """Configure human-readable and JSONL console output at one log level."""
    logger.remove()
    level = "DEBUG" if debug else "INFO"
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | <level>{message}</level>"
        ),
        filter=_exclude_jsonl,
        backtrace=debug,
        diagnose=debug,
    )
    logger.add(
        sys.stderr,
        level=level,
        format="{message}",
        filter=_include_jsonl,
        backtrace=debug,
        diagnose=debug,
    )


def _include_jsonl(record: dict[str, Any]) -> bool:
    return record["extra"].get(JSONL_LOG_MARKER) is True


def _exclude_jsonl(record: dict[str, Any]) -> bool:
    return not _include_jsonl(record)

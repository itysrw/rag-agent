"""Central Loguru configuration."""

import sys

from loguru import logger


def configure_logging(debug: bool) -> None:
    """Configure one console handler at the requested log level."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG" if debug else "INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | <level>{message}</level>"
        ),
        backtrace=debug,
        diagnose=debug,
    )

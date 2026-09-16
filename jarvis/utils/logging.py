"""Structured logging configuration that never serializes application settings or secrets."""

from __future__ import annotations

import sys

from loguru import logger


def configure_logging(level: str) -> None:
    """Configure the process logger once from the non-secret log level setting."""
    logger.remove()
    logger.add(sys.stderr, level=level.upper(), serialize=True, backtrace=False, diagnose=False)

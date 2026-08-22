"""
Central logging configuration.

The codebase previously used bare `print()` calls, which produce no timestamps,
no levels, and no way to filter or ship logs. This module configures loguru
(already a declared dependency) and exports a single `logger` for the whole app.

Usage:
    from app.core.logging import logger
    logger.info("Scraping {} for user {}", username, user_id)

Note loguru uses `{}` brace formatting with positional args, not %-formatting
and not f-strings — passing args separately means the string is only formatted
if the level is actually enabled.
"""

import sys

from loguru import logger

from app.core.config import settings

# Remove loguru's default handler so we do not double-log.
logger.remove()

_LEVEL = "DEBUG" if settings.env.lower() in ("dev", "development", "local") else "INFO"

logger.add(
    sys.stdout,
    level=_LEVEL,
    backtrace=False,   # do not dump full stack frames into production logs
    diagnose=False,    # CRITICAL: prevents variable values (secrets, tokens) leaking into tracebacks
    enqueue=False,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
)

__all__ = ["logger"]

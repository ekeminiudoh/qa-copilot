"""Logger configuration."""

import logging
import sys

from loguru import logger


def setup_logger(level: str = "INFO"):
    """Setup loguru logger."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
    )
    logger.add(
        "logs/qa-copilot.log",
        rotation="500 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=level,
    )
    return logger

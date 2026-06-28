"""Core logger module."""

import logging
import sys
from pathlib import Path

from loguru import logger


def setup_logger(level: str = "INFO"):
    """Setup loguru logger with file and console output."""
    # Remove default handlers
    logger.remove()

    # Console output
    logger.add(
        sys.stdout,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
    )

    # File output
    log_path = Path(__file__).resolve().parent.parent.parent / "logs"
    log_path.mkdir(exist_ok=True)

    logger.add(
        str(log_path / "qa-copilot.log"),
        rotation="500 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=level,
    )

    return logger

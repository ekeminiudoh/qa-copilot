"""Utility functions."""

import hashlib
from typing import Any


def generate_id(data: str) -> str:
    """Generate a unique ID from data."""
    return hashlib.md5(data.encode()).hexdigest()


def truncate(text: str, max_length: int = 100) -> str:
    """Truncate text to max length."""
    return text[: max_length - 3] + "..." if len(text) > max_length else text

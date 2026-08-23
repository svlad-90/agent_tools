"""Public API for console output parsing."""

from __future__ import annotations

from ..src.console import ConsoleChunk
from ..src.console import parse_console_output

__all__ = [
    "ConsoleChunk",
    "parse_console_output",
]

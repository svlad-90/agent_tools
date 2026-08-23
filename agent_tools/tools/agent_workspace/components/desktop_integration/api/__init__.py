"""Public API for Linux desktop integration."""

from __future__ import annotations

from ..src.install_desktop import desktop_entry
from ..src.install_desktop import main

__all__ = [
    "desktop_entry",
    "main",
]

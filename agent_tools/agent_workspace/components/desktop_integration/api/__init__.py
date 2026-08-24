"""Public API for Linux desktop integration."""

from __future__ import annotations

from ..src.install_desktop import agent_workspace_icon_source
from ..src.install_desktop import agent_tools_package_root
from ..src.install_desktop import desktop_entry
from ..src.install_desktop import main
from ..src.install_desktop import workspace_root

__all__ = [
    "agent_tools_package_root",
    "agent_workspace_icon_source",
    "desktop_entry",
    "main",
    "workspace_root",
]

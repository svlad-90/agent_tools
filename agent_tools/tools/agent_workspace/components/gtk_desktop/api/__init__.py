"""Public API for the Agent Workspace GTK desktop frontend."""

from __future__ import annotations

from ..src.gtk_ui import TerminalSession
from ..src.gtk_ui import WorkspaceGtkGui
from ..src.gtk_ui import main
from ..src.gtk_ui import open_artifact_path
from ..src.gtk_ui import open_containing_folder
from ..src.gtk_ui import open_path
from ..src.gtk_ui import open_text_file

__all__ = [
    "TerminalSession",
    "WorkspaceGtkGui",
    "main",
    "open_artifact_path",
    "open_containing_folder",
    "open_path",
    "open_text_file",
]

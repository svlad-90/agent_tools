"""Shared PAF task helpers for the Yocto domain."""

from __future__ import annotations

from paf_workspace.tasks import WorkspaceTask


class check_workspace_environment(WorkspaceTask):
    """Check workspace paths required by generic Yocto PAF tasks."""

    def __init__(self):
        super().__init__()
        self.set_name(check_workspace_environment.__name__)

    def execute(self):
        root = self.workspace_root()
        self.assertion(root.exists(), f"WORKSPACE_ROOT does not exist: {root}")

        paf_root = self.path_param("PAF_ROOT")
        self.assertion((paf_root / "paf_main.py").exists(), f"PAF is incomplete: {paf_root}")

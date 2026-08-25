from __future__ import annotations

from pathlib import Path

import pytest

from paf_workspace.logs import PafLogDirError
from paf_workspace.logs import resolve_paf_log_dir


def test_resolve_paf_log_dir_uses_agent_task_env(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample"
    _make_task(task)

    assert resolve_paf_log_dir(
        workspace_root=workspace,
        cwd=workspace,
        config_path=workspace / "agent_tools" / "paf_workspace" / "domains" / "demo.xml",
        env={"AGENT_TOOLS_TASK_DIR": str(task)},
    ) == task / "report" / "logs" / "paf"


def test_resolve_paf_log_dir_uses_current_task_path(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample"
    nested = task / "dev" / "repo"
    _make_task(task)
    nested.mkdir(parents=True)

    assert resolve_paf_log_dir(
        workspace_root=workspace,
        cwd=nested,
        config_path=workspace / "agent_tools" / "paf_workspace" / "domains" / "demo.xml",
        env={},
    ) == task / "report" / "logs" / "paf"


def test_resolve_paf_log_dir_uses_task_local_config_path(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample"
    _make_task(task)
    config = task / "scripts" / "paf" / "scenario.xml"
    config.parent.mkdir(parents=True)
    config.write_text("<paf_config/>", encoding="utf-8")

    assert resolve_paf_log_dir(
        workspace_root=workspace,
        cwd=workspace,
        config_path=config,
        env={},
    ) == task / "report" / "logs" / "paf"


def test_resolve_paf_log_dir_requires_task_context(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "tasks" / "sample").mkdir(parents=True)

    with pytest.raises(PafLogDirError):
        resolve_paf_log_dir(
            workspace_root=workspace,
            cwd=workspace / "tasks" / "sample",
            config_path=workspace / "agent_tools" / "paf_workspace" / "domains" / "demo.xml",
            env={},
        )


def test_resolve_paf_log_dir_rejects_workspace_root_fallback(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(PafLogDirError):
        resolve_paf_log_dir(
            workspace_root=workspace,
            cwd=workspace,
            config_path=workspace / "agent_tools" / "paf_workspace" / "domains" / "demo.xml",
            env={},
        )


def _make_task(task: Path) -> None:
    (task / "report" / "logs").mkdir(parents=True)
    (task / "TASK_CONTEXT.sqlite3").write_bytes(b"sqlite")

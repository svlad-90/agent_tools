from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_tools.agent_workspace.components.test_support.src.helpers import *


def test_create_agent_workspace_writes_manifest_and_tasks_dir(tmp_path: Path) -> None:
    workspace = tmp_path / "work"

    manifest = create_agent_workspace(workspace, name="Main Work")

    assert manifest.name == "Main Work"
    assert manifest.schema_version == AGENT_WORKSPACE_SCHEMA_VERSION
    assert (workspace / ".agent-workspace" / "workspace.json").is_file()
    assert (workspace / "tasks").is_dir()
    assert load_agent_workspace_manifest(workspace).workspace_id == manifest.workspace_id


def test_load_agent_workspace_manifest_rejects_absolute_tasks_dir(tmp_path: Path) -> None:
    workspace = tmp_path / "work"
    manifest_path = workspace / ".agent-workspace" / "workspace.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "workspace_id": "id",
                "name": "work",
                "created_at": "2026-08-28T00:00:00Z",
                "agent_workspace_min_version": "2.1.0",
                "tasks_dir": "/tmp/tasks",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid tasks_dir"):
        load_agent_workspace_manifest(workspace)


def test_resolve_agent_workspace_startup_prefers_last_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings_path = tmp_path / "settings.json"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    last_workspace = tmp_path / "last"
    cwd_workspace = tmp_path / "cwd"
    create_agent_workspace(last_workspace)
    create_agent_workspace(cwd_workspace)
    save_agent_workspace_settings({"last_workspace": str(last_workspace)}, settings_path)
    monkeypatch.setattr(
        "agent_tools.agent_workspace.components.settings.src.settings.agent_workspace_settings_path",
        lambda: settings_path,
    )

    assert resolve_agent_workspace_startup(cwd=cwd_workspace) == last_workspace.resolve()


def test_resolve_agent_workspace_startup_creates_explicit_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr(
        "agent_tools.agent_workspace.components.settings.src.settings.agent_workspace_settings_path",
        lambda: settings_path,
    )
    workspace = tmp_path / "new-work"

    assert resolve_agent_workspace_startup(workspace, cwd=tmp_path) == workspace.resolve()
    assert (workspace / ".agent-workspace" / "workspace.json").is_file()
    assert load_agent_workspace_settings(settings_path)["last_workspace"] == str(workspace.resolve())

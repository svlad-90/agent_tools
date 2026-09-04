from __future__ import annotations

from pathlib import Path

import pytest

from paf_workspace.logs import PafLogDirError
from paf_workspace.logs import clear_log_dir
from paf_workspace.logs import finish_paf_log_run
from paf_workspace.logs import main
from paf_workspace.logs import prepare_paf_log_run
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


def test_clear_log_dir_removes_existing_log_contents(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "old.log").write_text("old", encoding="utf-8")
    nested = log_dir / "nested"
    nested.mkdir()
    (nested / "old.log").write_text("old", encoding="utf-8")

    clear_log_dir(log_dir)

    assert list(log_dir.iterdir()) == []


def test_paf_log_run_cleanup_preserves_active_parallel_runs(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    first = prepare_paf_log_run(log_dir)
    (first / "paf.log").write_text("first", encoding="utf-8")
    second = prepare_paf_log_run(log_dir)
    (second / "paf.log").write_text("second", encoding="utf-8")

    assert first.is_dir()
    assert second.is_dir()

    finish_paf_log_run(first)

    assert first.is_dir()
    assert second.is_dir()

    finish_paf_log_run(second)

    assert first.is_dir()
    assert second.is_dir()
    assert (second / "paf.log").read_text(encoding="utf-8") == "second"


def test_logs_cli_can_clear_resolved_paf_log_dir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample"
    _make_task(task)
    log_dir = task / "report" / "logs" / "paf"
    log_dir.mkdir(parents=True)
    (log_dir / "old.log").write_text("old", encoding="utf-8")

    result = main(
        [
            "--workspace-root",
            str(workspace),
            "--cwd",
            str(task),
            "--config",
            str(workspace / "agent_tools" / "paf_workspace" / "domains" / "demo.xml"),
            "--clear-existing",
        ]
    )

    assert result == 0
    assert capsys.readouterr().out.strip() == str(log_dir)
    assert list(log_dir.iterdir()) == []


def test_logs_cli_can_prepare_and_finish_paf_log_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample"
    _make_task(task)
    log_dir = task / "report" / "logs" / "paf"
    old_run = log_dir / "paf_2026_01_01_00_00_00_1_old"
    old_run.mkdir(parents=True)
    (old_run / "paf.log").write_text("old", encoding="utf-8")

    common_args = [
        "--workspace-root",
        str(workspace),
        "--cwd",
        str(task),
        "--config",
        str(workspace / "agent_tools" / "paf_workspace" / "domains" / "demo.xml"),
    ]
    assert main([*common_args, "--prepare-run"]) == 0
    run_dir = Path(capsys.readouterr().out.strip())
    assert run_dir.parent == log_dir
    assert run_dir.is_dir()
    assert not old_run.exists()

    (run_dir / "paf.log").write_text("new", encoding="utf-8")
    assert main([*common_args, "--finish-run", str(run_dir)]) == 0

    assert Path(capsys.readouterr().out.strip()) == run_dir
    assert run_dir.is_dir()
    assert (run_dir / "paf.log").read_text(encoding="utf-8") == "new"


def _make_task(task: Path) -> None:
    (task / "report" / "logs").mkdir(parents=True)
    (task / "TASK_CONTEXT.sqlite3").write_bytes(b"sqlite")

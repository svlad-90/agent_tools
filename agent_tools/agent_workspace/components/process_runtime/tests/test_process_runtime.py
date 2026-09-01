from __future__ import annotations

import pytest

from agent_tools.agent_workspace.components.test_support.src.helpers import *
from agent_tools.agent_workspace.components.process_runtime.src import runtime as process_runtime_module


def test_log_agent_workspace_exception_writes_traceback_to_workspace_root(tmp_path: Path) -> None:
    try:
        raise RuntimeError("boom")
    except RuntimeError as error:
        log_agent_workspace_exception(tmp_path, "test", type(error), error, error.__traceback__)

    log_path = tmp_path / "agent-workspace-crash.log"
    content = log_path.read_text(encoding="utf-8")
    assert "Agent Workspace test exception" in content
    assert "RuntimeError: boom" in content


def test_agent_workspace_lock_allows_single_running_instance(tmp_path: Path) -> None:
    first = acquire_agent_workspace_lock(tmp_path)
    assert first is not None
    try:
        assert acquire_agent_workspace_lock(tmp_path) is None
    finally:
        first.close()

    second = acquire_agent_workspace_lock(tmp_path)
    assert second is not None
    second.close()


def test_agent_workspace_failed_lock_does_not_truncate_owner_pid(tmp_path: Path) -> None:
    first = acquire_agent_workspace_lock(tmp_path)
    assert first is not None
    lock_path = process_runtime_module.agent_workspace_lock_path(tmp_path)
    owner = lock_path.read_text(encoding="utf-8")

    try:
        assert acquire_agent_workspace_lock(tmp_path) is None
        assert lock_path.read_text(encoding="utf-8") == owner
    finally:
        first.close()


def test_agent_workspace_lock_surfaces_filesystem_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(process_runtime_module, "agent_workspace_lock_path", lambda _workspace: tmp_path)

    with pytest.raises(OSError):
        acquire_agent_workspace_lock(tmp_path)


def test_abort_agent_workspace_with_stack_dump_writes_traceback_then_aborts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dumped: list[bool] = []
    aborted: list[bool] = []
    monkeypatch.setattr(process_runtime_module.faulthandler, "dump_traceback", lambda **_kwargs: dumped.append(True))
    monkeypatch.setattr(process_runtime_module.os, "abort", lambda: aborted.append(True))

    process_runtime_module.abort_agent_workspace_with_stack_dump(tmp_path, "test")

    content = (tmp_path / "agent-workspace-crash.log").read_text(encoding="utf-8")
    assert "Agent Workspace test forced stack dump" in content
    assert dumped == [True]
    assert aborted == [True]

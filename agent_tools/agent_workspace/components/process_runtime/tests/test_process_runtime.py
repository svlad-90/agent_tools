from __future__ import annotations

from agent_tools.agent_workspace.components.test_support.src.helpers import *


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


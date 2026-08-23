from __future__ import annotations

from agent_tools.agent_workspace.components.test_support.src.helpers import *


def test_agent_workspace_actions_task_check_uses_compact_output(tmp_path: Path, capsys: object) -> None:
    task = tmp_path / "tasks" / "sample-task"
    for rel_path in ("dev", "Dockerfile", "scripts", "report/diff", "report/puml"):
        (task / rel_path).mkdir(parents=True, exist_ok=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(task)

    exit_code = actions_main(["task-check", "--workspace", str(tmp_path), "--task", str(task)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Summary:" in captured.out
    assert "PASS task-description" not in captured.out


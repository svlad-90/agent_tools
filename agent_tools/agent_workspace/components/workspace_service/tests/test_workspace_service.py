from __future__ import annotations

from agent_tools.agent_workspace.components.test_support.src.helpers import *
from agent_tools.agent_workspace.components.harness_adapter.src.commands import handle_codex_adapter_hook


def test_agent_workspace_service_returns_headless_task_snapshot(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    report = task / "report"
    report.mkdir(parents=True)
    set_slot(task, "goal", "Headless service.")
    set_slot(task, "findings", "Agent Workspace service returns task data without importing GTK or VTE.")
    (task / "TASK_ACTIONS.json").write_text(
        json.dumps(
            {
                "actions": [
                    {
                        "id": "smoke",
                        "label": "Smoke",
                        "command": ["python3", "-c", "print('ok')"],
                        "cwd": ".",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (report / "runtime.log").write_text("log", encoding="utf-8")

    service = AgentWorkspaceService(tmp_path)
    handle_codex_adapter_hook(
        json.dumps(
            {
                "hook_event_name": "PreToolUse",
                "task_dir": str(task),
                "session_id": "s1",
                "tool_name": "exec_command",
                "tool_input": {"command": "python3 -c 'print(42)'"},
            }
        )
    )
    snapshot = service.task_snapshot("sample-task")

    assert snapshot["task"]["name"] == "sample-task"
    assert "Headless service" in snapshot["description"]
    assert "Agent Workspace service returns task data" in snapshot["context"]["markdown"]
    action_ids = [action["id"] for action in snapshot["actions"]["actions"]]
    assert action_ids[:2] == ["workspace:validate", "workspace:task-check"]
    assert "smoke" in action_ids
    assert snapshot["ai_debug"][0]["session_id"] == "s1"
    assert snapshot["ai_debug"][0]["tool_detail"] == "python3 -c 'print(42)'"
    assert snapshot["artifacts"][0]["label"] == "report/runtime.log"
    assert "python" in service.task_action_command("sample-task", "smoke")


def test_agent_workspace_service_renders_encoded_context_cards(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    set_slot(
        task,
        "findings",
        (
            "drivers/firmware/scmi/scmi.c records active context. "
            "drivers/firmware/scmi/scmi.c appears in the handoff. "
            "drivers/firmware/scmi/scmi.c remains the target file."
        ),
    )
    add_entry(
        task,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("bug",),
        summary="drivers/firmware/scmi/scmi.c has active context",
        details=(
            "drivers/firmware/scmi/scmi.c records active context. "
            "drivers/firmware/scmi/scmi.c appears in the handoff. "
            "drivers/firmware/scmi/scmi.c remains the target file."
        ),
    )
    summary = discover_tasks_with_context(task, tmp_path)
    entries = load_task_context_entries(task)

    markdown = encoded_context_entries_markdown(summary.path, entries)
    context = AgentWorkspaceService(tmp_path).task_context(
        "sample-task",
        filters=TaskContextFilters(severity=("high",), statuses=("active",)),
        encoded=True,
    )

    assert markdown.startswith("## Dictionary")
    assert "§00 = drivers/firmware/scmi/scmi.c" in markdown
    assert "#1 [HIGH] [ACTIVE]" in markdown
    assert "[HIGH] [ACTIVE]" in markdown
    assert context["dictionary"][0]["token"] == "§00"
    assert context["dictionary"][0]["value"] == "drivers/firmware/scmi/scmi.c"
    assert context["entries"][0]["category"] == "findings"
    assert "§00 records active context" in context["markdown"]

from __future__ import annotations

import subprocess

import pytest

from agent_tools.agent_workspace.components.test_support.src.helpers import *
from agent_tools.agent_workspace.components.harness_adapter.src.commands import handle_codex_adapter_hook
from agent_tools.agent_workspace.components.workspace_service.src import service as service_module


def test_agent_workspace_service_creates_task_without_catalog_refresh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AgentWorkspaceService(tmp_path)
    run_calls: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        run_calls.append(command)
        ensure_task_context_database(Path(command[3]))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(service_module.subprocess, "run", fake_run)
    monkeypatch.setattr(
        service_module,
        "discover_tasks",
        lambda _workspace: (_ for _ in ()).throw(AssertionError("full refresh should not run")),
    )

    result = service.create_task(" new-task ", privacy="private")

    assert result["task"]["name"] == "new-task"
    assert result["task"]["path"] == str(tmp_path / "tasks" / "new-task")
    assert run_calls[0][-2:] == ["--privacy", "private"]
    assert not list((tmp_path / "tasks").glob(".agent-workspace-create-*"))


def test_agent_workspace_service_cleans_failed_task_reservation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AgentWorkspaceService(tmp_path)
    task_path = tmp_path / "tasks" / "broken-task"

    def fail_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        (Path(command[3]) / "partial.txt").write_text("partial", encoding="utf-8")
        return subprocess.CompletedProcess(command, 2, "", "init failed")

    monkeypatch.setattr(service_module.subprocess, "run", fail_run)

    with pytest.raises(RuntimeError, match="init failed"):
        service.create_task("broken-task")

    assert not task_path.exists()


def test_agent_workspace_service_does_not_delete_replaced_task_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AgentWorkspaceService(tmp_path)
    task_path = tmp_path / "tasks" / "raced-task"

    def create_target_then_fail(
        command: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        task_path.mkdir()
        (task_path / "other-owner.txt").write_text("keep", encoding="utf-8")
        return subprocess.CompletedProcess(command, 2, "", "init failed")

    monkeypatch.setattr(service_module.subprocess, "run", create_target_then_fail)

    with pytest.raises(RuntimeError, match="init failed"):
        service.create_task("raced-task")

    assert (task_path / "other-owner.txt").read_text(encoding="utf-8") == "keep"


def test_agent_workspace_service_bounds_task_initialization_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AgentWorkspaceService(tmp_path)
    seen_timeout: list[object] = []

    def time_out(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen_timeout.append(kwargs["timeout"])
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(service_module.subprocess, "run", time_out)

    with pytest.raises(subprocess.TimeoutExpired):
        service.create_task("slow-task")

    assert seen_timeout == [service_module.TASK_CREATION_TIMEOUT_SECONDS]
    assert not (tmp_path / "tasks" / "slow-task").exists()


def test_agent_workspace_service_ignores_staging_cleanup_after_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AgentWorkspaceService(tmp_path)

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        ensure_task_context_database(Path(command[3]))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(service_module.subprocess, "run", fake_run)
    monkeypatch.setattr(
        service_module.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(OSError("cleanup failed")),
    )

    result = service.create_task("published-task")

    assert result["task"]["name"] == "published-task"
    assert (tmp_path / "tasks" / "published-task" / "TASK_CONTEXT.sqlite3").is_file()


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
    assert action_ids[:3] == [
        "workspace:validate",
        "workspace:validate-push",
        "workspace:task-check",
    ]
    assert "smoke" in action_ids
    assert snapshot["ai_debug"][0]["session_id"] == "s1"
    assert snapshot["ai_debug"][0]["tool_detail"] == "python3 -c 'print(42)'"
    assert snapshot["artifacts"][0]["label"] == "report/runtime.log"
    assert "python" in service.task_action_command("sample-task", "smoke")


def test_agent_workspace_service_returns_bounded_artifact_content(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    artifact = task / "report" / "notes.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("browser preview", encoding="utf-8")
    set_slot(task, "goal", "Artifact preview task")
    service = AgentWorkspaceService(tmp_path)

    preview = service.artifact_content("sample-task", "report/notes.md")

    assert preview["content"] == "browser preview"
    assert preview["label"] == "report/notes.md"
    with pytest.raises(ValueError, match="unknown artifact"):
        service.artifact_content("sample-task", "../outside.txt")


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


def test_agent_workspace_service_updates_single_context_slot(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    set_slot(task, "findings", "Old finding")
    service = AgentWorkspaceService(tmp_path)

    result = service.save_task_context_slot(
        "sample-task",
        "findings",
        "  Browser mutation is transactional.  ",
    )

    assert result["slot"]["category"] == "findings"
    assert result["slot"]["content"] == "Browser mutation is transactional."
    assert result["context"]["entries"] == [result["slot"]]
    assert "Browser mutation is transactional." in result["context"]["markdown"]

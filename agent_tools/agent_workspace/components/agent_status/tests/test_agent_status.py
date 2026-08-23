from __future__ import annotations

from agent_tools.agent_workspace.components.test_support.src.helpers import *


def test_task_agent_status_text_combines_permission_running_and_saved_sessions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    save_task_agent_session(summary, "claude", session_id="019feba2-e25e-76e1-9468-aa3997582690")

    assert (
        task_agent_status_text(
            summary,
            workspace,
            permission_pending=True,
            running_agents=("codex",),
            spinner_frame="▷",
            home=home,
        )
        == "▷"
    )
    assert (
        task_agent_status_text(
            summary,
            workspace,
            permission_pending=False,
            running_agents=("codex",),
            spinner_frame="▷",
            home=home,
        )
        == "▷"
    )
    assert (
        task_agent_status_text(
            summary,
            workspace,
            permission_pending=False,
            running_agents=("codex",),
            spinner_frame="",
            home=home,
        )
        == "▷"
    )


def test_task_agent_status_text_shows_saved_sessions_only_when_no_agent_is_running(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    codex_session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    codex_session_file = home / ".codex" / "sessions" / f"{codex_session_id}.jsonl"
    codex_session_file.parent.mkdir(parents=True)
    codex_session_file.write_text("{}", encoding="utf-8")
    save_task_agent_session(summary, "codex", session_id=codex_session_id)
    save_task_agent_session(summary, "claude", session_id="019feba2-e25e-76e1-9468-aa3997582690")

    assert (
        task_agent_status_text(
            summary,
            workspace,
            permission_pending=False,
            running_agents=(),
            external_active=True,
            spinner_frame="▷",
            home=home,
        )
        == "×"
    )
    assert (
        task_agent_status_text(
            summary,
            workspace,
            permission_pending=False,
            running_agents=("codex",),
            external_active=True,
            spinner_frame="▷",
            home=home,
        )
        == "×"
    )
    assert (
        task_agent_status_text(
            summary,
            workspace,
            permission_pending=False,
            running_agents=(),
            external_active=False,
            spinner_frame="▷",
            home=home,
        )
        == "Ⅱ"
    )


def test_agent_status_tooltip_explains_visible_markers_compactly() -> None:
    assert agent_status_tooltip_text("Ⅱ") == "Сессию можно продолжить"
    assert agent_status_tooltip_text("□") == "Нет сохраненной сессии"
    assert agent_status_tooltip_text("▷") == "Агент запущен"
    assert agent_status_tooltip_text("×") == "Задача занята другим окном"


def test_agent_status_manual_entries_are_structured_for_popup() -> None:
    assert AGENT_STATUS_MANUAL_MENU_LABEL == "Manual"
    assert AGENT_STATUS_MANUAL_TITLE == "Manual"
    assert [entry[0] for entry in AGENT_STATUS_MANUAL_USAGE_ENTRIES] == [
        "Концепция",
        "Задачи",
        "Агент",
        "Копирование",
        "Структура",
        "Действия",
        "Сброс",
    ]
    assert [entry[0] for entry in AGENT_STATUS_MANUAL_ENTRIES] == ["Ⅱ", "□", "▷", "×"]
    assert all(len(entry) == 3 for entry in AGENT_STATUS_MANUAL_ENTRIES)


def test_task_status_label_prefixes_permission_and_agent_session_markers() -> None:
    assert task_status_label("sample-task", permission_pending=False) == "sample-task"
    assert (
        task_status_label(
            "sample-task",
            permission_pending=True,
            session_markers=("Ⅱ",),
        )
        == "Ⅱ sample-task"
    )


def test_task_for_path_returns_existing_or_fallback_summary(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    missing_path = tmp_path / "tasks" / "missing-task"

    assert task_for_path([summary], task) is summary
    fallback = task_for_path([summary], missing_path)

    assert fallback.name == "missing-task"
    assert fallback.path == missing_path
    assert not fallback.has_description
    assert not fallback.has_context
    assert fallback.description_tokens == 0
    assert fallback.context_tokens == 0
    assert not fallback.context_over_budget


def test_agent_output_requests_permission_ignores_approval_prompts() -> None:
    assert not agent_output_requests_permission("Command requires approval before running.")
    assert not agent_output_requests_permission("Do you want to allow this command? yes/no")
    assert not agent_output_requests_permission("\x1b[31mPermission required\x1b[0m")
    assert not agent_output_requests_permission(
        "Would you like to run the following command?\n\n"
        "  Environment: local\n\n"
        "  $ true\n\n"
        "› 1. Yes, proceed (y)\n"
        "  2. Yes, and don't ask again for commands that start with `true` (p)\n"
        "  3. No, and tell Codex what to do differently (esc)\n"
    )
    assert not agent_output_requests_permission("Build completed successfully.")


def test_analyze_agent_output_reports_missing_session_and_permission() -> None:
    analysis = analyze_agent_output(
        "\x1b]0;title\x07No conversation found with session ID: "
        "71ca3372-3c10-4501-ad2a-145c5b9305de\r"
        "Would you like to run the following command?"
    )

    assert analysis.missing_session
    assert not analysis.requests_permission
    assert analysis.permission_signature is None
    assert not analysis.turn_complete


def test_agent_output_requests_permission_ignores_choice_prompt() -> None:
    analysis = analyze_agent_output("Allow this command to run? [y/N]")

    assert not analysis.requests_permission
    assert analysis.permission_signature is None


def test_agent_output_permission_scanner_ignores_large_terminal_tail() -> None:
    tail = ("normal output \x1b[31mwith color\x1b[0m\n" * 400) + "Allow this command to run? [y/N]\n"

    analysis = analyze_agent_output(tail)

    assert not analysis.requests_permission
    assert analysis.permission_signature is None


def test_agent_output_reports_turn_complete_for_completion_summaries() -> None:
    assert agent_output_reports_turn_complete("Done.\n")
    assert agent_output_reports_turn_complete("Tokens used: 12,345\n")
    assert agent_output_reports_turn_complete("Cost: $0.10\n")
    assert not agent_output_reports_turn_complete("Would you like to run the following command?")


def test_agent_output_state_update_prioritizes_missing_session() -> None:
    update = agent_output_state_update(
        "No conversation found with session ID: 71ca3372-3c10-4501-ad2a-145c5b9305de\n"
        "Would you like to run the following command?",
        exited=False,
        permission_pending=True,
    )

    assert update.missing_session
    assert update.exited
    assert not update.permission_requested
    assert not update.permission_pending


def test_agent_output_state_update_does_not_mark_permission_prompts() -> None:
    update = agent_output_state_update(
        "Would you like to run the following command?",
        exited=False,
        permission_pending=False,
    )
    pending_update = agent_output_state_update(
        "Would you like to run the following command?",
        exited=False,
        permission_pending=True,
    )
    exited_update = agent_output_state_update(
        "Would you like to run the following command?",
        exited=True,
        permission_pending=False,
    )

    assert not update.permission_requested
    assert not update.permission_pending
    assert not pending_update.permission_requested
    assert pending_update.permission_pending
    assert not exited_update.permission_requested
    assert exited_update.exited


def test_session_is_running_agent_requires_known_agent_and_live_session() -> None:
    assert session_is_running_agent(session_kind="codex", exited=False)
    assert session_is_running_agent(session_kind="claude", exited=False)
    assert not session_is_running_agent(session_kind="shell", exited=False)
    assert not session_is_running_agent(session_kind="codex", exited=True)


def test_session_is_agent_accepts_supported_agent_kinds_only() -> None:
    assert session_is_agent(session_kind="codex")
    assert session_is_agent(session_kind="claude")
    assert not session_is_agent(session_kind="shell")
    assert not session_is_agent(session_kind="")


def test_session_should_clear_pending_permission_only_for_pending_agent() -> None:
    assert session_should_clear_pending_permission(session_kind="codex", permission_pending=True)
    assert session_should_clear_pending_permission(session_kind="claude", permission_pending=True)
    assert not session_should_clear_pending_permission(session_kind="shell", permission_pending=True)
    assert not session_should_clear_pending_permission(session_kind="codex", permission_pending=False)


def test_session_marks_task_running_agent_requires_live_agent_for_task() -> None:
    task_path = Path("/tmp/workspace/tasks/sample-task")

    assert session_marks_task_running_agent(
        session_kind="claude",
        session_task_path=task_path,
        exited=False,
        task_path=task_path,
    )
    assert not session_marks_task_running_agent(
        session_kind="shell",
        session_task_path=task_path,
        exited=False,
        task_path=task_path,
    )
    assert not session_marks_task_running_agent(
        session_kind="codex",
        session_task_path=task_path,
        exited=True,
        task_path=task_path,
    )
    assert not session_marks_task_running_agent(
        session_kind="codex",
        session_task_path=task_path / "other",
        exited=False,
        task_path=task_path,
    )


def test_session_marks_task_pending_permission_only_for_live_agent_task() -> None:
    task_path = Path("/tmp/workspace/tasks/sample-task")

    assert session_marks_task_pending_permission(
        session_kind="claude",
        session_task_path=task_path,
        permission_pending=True,
        exited=False,
        task_path=task_path,
    )
    assert not session_marks_task_pending_permission(
        session_kind="shell",
        session_task_path=task_path,
        permission_pending=True,
        exited=False,
        task_path=task_path,
    )
    assert not session_marks_task_pending_permission(
        session_kind="codex",
        session_task_path=task_path,
        permission_pending=True,
        exited=True,
        task_path=task_path,
    )
    assert not session_marks_task_pending_permission(
        session_kind="codex",
        session_task_path=task_path / "other",
        permission_pending=True,
        exited=False,
        task_path=task_path,
    )


def test_agent_output_reports_missing_session_detects_cli_error() -> None:
    assert agent_output_reports_missing_session(
        "No conversation found with session ID: 71ca3372-3c10-4501-ad2a-145c5b9305de"
    )
    assert not agent_output_reports_missing_session("Conversation resumed.")


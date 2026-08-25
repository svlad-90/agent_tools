from __future__ import annotations

import json

from agent_tools.agent_workspace.components.test_support.src.helpers import *


def _joined_pairs(command: list[str]) -> list[str]:
    return [f"{left} {right}" for left, right in zip(command, command[1:])]


def _claude_settings(command: list[str]) -> dict[str, object]:
    index = command.index("--settings")
    return json.loads(command[index + 1])


def _assert_codex_low_redraw_tui_options(command: list[str]) -> None:
    joined_pairs = _joined_pairs(command)
    assert "-c tui.animations=false" in joined_pairs
    assert "-c tui.disable_mouse_capture=true" in joined_pairs


def test_codex_tui_animations_can_be_enabled(tmp_path: Path) -> None:
    command = build_ai_agent_console_command(
        tmp_path,
        "task prompt",
        "codex",
        codex_executable="codex-bin",
        claude_executable="claude-bin",
        codex_animations_enabled=True,
    )

    joined_pairs = _joined_pairs(command)
    assert "-c tui.animations=false" not in joined_pairs
    assert "-c tui.disable_mouse_capture=true" in joined_pairs


def test_claude_tui_animations_can_be_enabled(tmp_path: Path) -> None:
    command = build_ai_agent_console_command(
        tmp_path,
        "task prompt",
        "claude",
        codex_executable="codex-bin",
        claude_executable="claude-bin",
        claude_animations_enabled=True,
    )

    assert _claude_settings(command)["prefersReducedMotion"] is False


def test_codex_task_context_message_points_at_selected_task(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    message = codex_task_context_message(summary, tmp_path)

    assert "workspace task `sample-task`" in message
    assert f"Workspace: {tmp_path}" in message
    assert f"Task directory: {task}" in message
    assert "Workspace policy is delivered by harness hooks" in message
    assert "front_door_bell.py" not in message
    assert "Current task context slots preloaded from `TASK_CONTEXT.sqlite3`" not in message


def test_core_ai_agent_task_context_prompt_supports_optional_suffix(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    plain = ai_agent_task_context_prompt(summary, tmp_path, inject_task_context=False)
    suffixed = ai_agent_task_context_prompt(
        summary,
        tmp_path,
        "Reply in Russian.",
        inject_task_context=False,
    )

    assert "Workspace policy is delivered by harness hooks" in plain
    assert "front_door_bell.py" not in plain
    assert "--open-iteration" not in plain
    assert "Reply in Russian." not in plain
    assert suffixed.endswith("Reply in Russian.")
    assert "Current task context slots preloaded" not in plain


def test_ai_agent_task_context_prompt_does_not_inject_active_context(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    set_slot(
        task,
        "findings",
        (
            "drivers/firmware/scmi/scmi.c records current context. "
            "drivers/firmware/scmi/scmi.c appears in the handoff. "
            "drivers/firmware/scmi/scmi.c remains the target file."
        ),
    )
    summary = discover_tasks_with_context(task, tmp_path)

    prompt = ai_agent_task_context_prompt(summary, tmp_path)

    assert "Workspace policy is delivered by harness hooks" in prompt
    assert "front_door_bell.py" not in prompt
    assert "Current task context slots preloaded from `TASK_CONTEXT.sqlite3`" not in prompt
    assert "| Findings" not in prompt
    assert "records current context" not in prompt


def test_ai_agent_environment_exports_front_desk_session_identity(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    new_env = ai_agent_environment(
        {"PATH": "/bin"},
        summary,
        tmp_path,
        "codex",
        AgentSessionState(agent="codex", resume=False, session_id=None),
        run_id="run-1",
    )
    resumed_env = ai_agent_environment(
        {"PATH": "/bin"},
        summary,
        tmp_path,
        "codex",
        AgentSessionState(agent="codex", resume=True, session_id="codex-session-1"),
        run_id="run-2",
    )
    claude_env = ai_agent_environment(
        {"PATH": "/bin"},
        summary,
        tmp_path,
        "claude",
        AgentSessionState(agent="claude", resume=False, session_id=None),
        run_id="run-3",
        limited_bash_output_tokens=1_200,
    )

    assert new_env["AGENT_TOOLS_AGENT"] == "codex"
    assert new_env["AGENT_TOOLS_SESSION_ID"] == "run-1"
    assert new_env["AGENT_TOOLS_RUN_ID"] == "run-1"
    assert new_env["AGENT_TOOLS_TASK_DIR"] == str(task)
    assert new_env["AGENT_TOOLS_WORKSPACE"] == str(tmp_path)
    assert "CLAUDE_CODE_DISABLE_MOUSE" not in new_env
    assert "AGENT_TOOLS_AGENT_SESSION_ID" not in new_env
    assert resumed_env["AGENT_TOOLS_SESSION_ID"] == "codex-session-1"
    assert resumed_env["AGENT_TOOLS_AGENT_SESSION_ID"] == "codex-session-1"
    assert claude_env["CLAUDE_CODE_DISABLE_MOUSE"] == "1"
    assert claude_env["AGENT_TOOLS_LIMITED_BASH_OUTPUT_TOKENS"] == "1200"
    assert resumed_env["AGENT_TOOLS_RUN_ID"] == "run-2"


def test_task_check_errors_are_added_to_new_ai_prompt(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    summary = discover_tasks(tmp_path)[0]

    suffix = task_check_prompt_suffix(summary, tmp_path)

    assert "Task check reported errors" in suffix
    assert "task-context-slot-required" in suffix


def test_new_ai_launch_uses_harness_adapter_prompt_instead_of_task_check_dump(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    summary = discover_tasks(tmp_path)[0]

    launch = prepare_ai_agent_launch_command(
        summary,
        tmp_path,
        "codex",
        codex_model="gpt-5.5",
        codex_reasoning="medium",
        claude_model="sonnet",
        claude_effort="low",
        codex_executable="codex-bin",
        claude_executable="claude-bin",
        include_task_check=True,
    )

    assert "Workspace policy is delivered by harness hooks" in launch.command[-1]
    assert "front_door_bell.py" not in launch.command[-1]
    assert "Task check reported errors" not in launch.command[-1]
    assert "task-context-slot-required" not in launch.command[-1]


def test_resumed_ai_launch_uses_harness_adapter_prompt_instead_of_task_check_dump(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    summary = discover_tasks(tmp_path)[0]
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    session_file = home / ".codex" / "sessions" / f"{session_id}.jsonl"
    session_file.parent.mkdir(parents=True)
    session_file.write_text("{}", encoding="utf-8")
    save_task_agent_session(summary, "codex", session_id=session_id)

    launch = prepare_ai_agent_launch_command(
        summary,
        tmp_path,
        "codex",
        codex_model="gpt-5.5",
        codex_reasoning="medium",
        claude_model="sonnet",
        claude_effort="low",
        codex_executable="codex-bin",
        claude_executable="claude-bin",
        include_task_check=True,
    )

    assert launch.session_state.resume
    assert launch.command[-5:] == ["resume", "--cd", str(tmp_path), "--no-alt-screen", session_id]
    _assert_codex_low_redraw_tui_options(launch.command)
    assert all("Workspace policy is delivered by harness hooks" not in part for part in launch.command)
    assert all("front_door_bell.py" not in part for part in launch.command)
    assert all("Task check reported errors" not in part for part in launch.command)
    assert all("task-context-slot-required" not in part for part in launch.command)


def test_codex_console_command_passes_prompt_and_workspace(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = codex_console_command(tmp_path, summary)

    assert command[-4:] == [
        "--cd",
        str(tmp_path),
        "--no-alt-screen",
        codex_task_context_message(summary, tmp_path),
    ]
    _assert_codex_low_redraw_tui_options(command)


def test_core_ai_agent_command_builder_handles_codex_and_claude(tmp_path: Path) -> None:
    prompt = "task prompt"

    codex_command = build_ai_agent_console_command(
        tmp_path,
        prompt,
        "codex",
        codex_executable="codex-bin",
        claude_executable="claude-bin",
        model="gpt-5.5",
        reasoning_effort="medium",
    )
    claude_command = build_ai_agent_console_command(
        tmp_path,
        prompt,
        "claude",
        codex_executable="codex-bin",
        claude_executable="claude-bin",
        resume=True,
        resume_session_id="019feba2-e25e-76e1-9468-aa399758268f",
        model="sonnet",
        reasoning_effort="low",
    )

    assert codex_command[:5] == ["codex-bin", "--model", "gpt-5.5", "-c", 'model_reasoning_effort="medium"']
    assert "python3 -m agent_tools.agent_workspace.components.harness_adapter.codex" in " ".join(codex_command)
    assert codex_command[-4:] == ["--cd", str(tmp_path), "--no-alt-screen", prompt]
    _assert_codex_low_redraw_tui_options(codex_command)
    assert "-c tui.status_line=[]" not in _joined_pairs(codex_command)
    assert "-c tui.terminal_title=[]" not in _joined_pairs(codex_command)
    assert claude_command[:7] == [
        "claude-bin",
        "--permission-mode",
        "auto",
        "--model",
        "sonnet",
        "--effort",
        "low",
    ]
    assert "--ax-screen-reader" not in claude_command
    assert _claude_settings(claude_command)["prefersReducedMotion"] is True
    assert "python3 -m agent_tools.agent_workspace.components.harness_adapter.claude" in " ".join(claude_command)
    assert claude_command[-2:] == ["--resume", "019feba2-e25e-76e1-9468-aa399758268f"]
    assert prompt not in claude_command


def test_prepare_ai_agent_launch_command_builds_command_from_session_and_model_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    session_file = home / ".codex" / "sessions" / f"{session_id}.jsonl"
    session_file.parent.mkdir(parents=True)
    session_file.write_text("{}", encoding="utf-8")
    save_task_agent_session(summary, "codex", session_id=session_id)

    launch = prepare_ai_agent_launch_command(
        summary,
        tmp_path,
        "codex",
        codex_model="gpt-5.5",
        codex_reasoning="medium",
        claude_model="sonnet",
        claude_effort="low",
        codex_executable="codex-bin",
        claude_executable="claude-bin",
        prompt_suffix="Reply in Russian.",
    )

    assert launch.session_state.resume
    assert launch.session_state.session_id == session_id
    assert launch.model_settings.model == "gpt-5.5"
    assert launch.model_settings.reasoning_effort == "medium"
    assert launch.command[:5] == ["codex-bin", "--model", "gpt-5.5", "-c", 'model_reasoning_effort="medium"']
    assert "python3 -m agent_tools.agent_workspace.components.harness_adapter.codex" in " ".join(launch.command)
    assert launch.command[-5:] == ["resume", "--cd", str(tmp_path), "--no-alt-screen", session_id]
    _assert_codex_low_redraw_tui_options(launch.command)
    assert all("Workspace policy is delivered by harness hooks" not in part for part in launch.command)
    assert all("front_door_bell.py" not in part for part in launch.command)
    assert all("Current task context slots preloaded from `TASK_CONTEXT.sqlite3`" not in part for part in launch.command)


def test_codex_console_command_can_resume_session(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"

    command = codex_console_command(tmp_path, summary, resume=True, resume_session_id=session_id)

    assert command[-5:] == [
        "resume",
        "--cd",
        str(tmp_path),
        "--no-alt-screen",
        session_id,
    ]
    assert codex_task_context_message(summary, tmp_path) not in command


def test_codex_console_command_uses_model_and_reasoning(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = codex_console_command(tmp_path, summary, model="gpt-5.5", reasoning_effort="low")

    assert command[:5] == [command[0], "--model", "gpt-5.5", "-c", 'model_reasoning_effort="low"']
    _assert_codex_low_redraw_tui_options(command)
    assert "-c tui.show_tooltips=false" not in _joined_pairs(command)


def test_codex_console_command_resume_without_session_starts_new_task_context(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = codex_console_command(tmp_path, summary, resume=True, model="gpt-5.5", reasoning_effort="medium")

    assert command[:5] == [command[0], "--model", "gpt-5.5", "-c", 'model_reasoning_effort="medium"']
    _assert_codex_low_redraw_tui_options(command)
    assert command[-4:] == [
        "--cd",
        str(tmp_path),
        "--no-alt-screen",
        codex_task_context_message(summary, tmp_path),
    ]


def test_gtk_and_tk_codex_command_builders_match(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    tk_command = ai_agent_console_command(
        tmp_path,
        summary,
        "codex",
        model="gpt-5.5",
        reasoning_effort="medium",
    )
    gtk_command = gtk_ai_agent_console_command(
        tmp_path,
        summary,
        "codex",
        model="gpt-5.5",
        reasoning_effort="medium",
    )

    assert gtk_command[:-1] == tk_command[:-1]
    assert "--permission-mode" not in tk_command
    assert "--permission-mode" not in gtk_command
    assert "workspace task `sample-task`" in gtk_command[-1]
    assert "workspace task `sample-task`" in tk_command[-1]


def test_ai_agent_console_command_supports_claude(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = ai_agent_console_command(tmp_path, summary, "claude")

    assert command[0].endswith("claude")
    assert command[1:3] == ["--permission-mode", "auto"]
    assert "--ax-screen-reader" not in command
    assert _claude_settings(command)["prefersReducedMotion"] is True
    assert "workspace task `sample-task`" in command[-1]


def test_ai_agent_console_command_uses_claude_model_and_effort(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = ai_agent_console_command(tmp_path, summary, "claude", model="sonnet", reasoning_effort="low")

    assert command[:7] == [
        command[0],
        "--permission-mode",
        "auto",
        "--model",
        "sonnet",
        "--effort",
        "low",
    ]
    assert "--ax-screen-reader" not in command
    assert _claude_settings(command)["prefersReducedMotion"] is True
    assert "workspace task `sample-task`" in command[-1]


def test_ai_agent_console_command_starts_claude_when_resume_has_no_session_id(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = ai_agent_console_command(tmp_path, summary, "claude", resume=True)

    assert command[0].endswith("claude")
    assert command[1:3] == ["--permission-mode", "auto"]
    assert "--ax-screen-reader" not in command
    assert _claude_settings(command)["prefersReducedMotion"] is True
    assert "--continue" not in command
    assert "workspace task `sample-task`" in command[-1]


def test_ai_agent_console_command_can_use_claude_session_id(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"

    first_command = ai_agent_console_command(tmp_path, summary, "claude", resume_session_id=session_id)
    resume_command = ai_agent_console_command(
        tmp_path,
        summary,
        "claude",
        resume=True,
        resume_session_id=session_id,
    )

    assert first_command[:3] == [first_command[0], "--permission-mode", "auto"]
    assert "--ax-screen-reader" not in first_command
    assert _claude_settings(first_command)["prefersReducedMotion"] is True
    assert "python3 -m agent_tools.agent_workspace.components.harness_adapter.claude" in " ".join(first_command)
    assert first_command[-3:-1] == ["--session-id", session_id]
    assert "workspace task `sample-task`" in first_command[-1]
    assert resume_command[:3] == [resume_command[0], "--permission-mode", "auto"]
    assert "--ax-screen-reader" not in resume_command
    assert _claude_settings(resume_command)["prefersReducedMotion"] is True
    assert "python3 -m agent_tools.agent_workspace.components.harness_adapter.claude" in " ".join(resume_command)
    assert resume_command[-2:] == ["--resume", session_id]
    assert all("workspace task `sample-task`" not in part for part in resume_command)


def test_gtk_and_tk_claude_command_builders_match(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"

    tk_command = ai_agent_console_command(
        tmp_path,
        summary,
        "claude",
        resume=True,
        resume_session_id=session_id,
        model="sonnet",
        reasoning_effort="medium",
    )
    gtk_command = gtk_ai_agent_console_command(
        tmp_path,
        summary,
        "claude",
        "",
        resume=True,
        resume_session_id=session_id,
        model="sonnet",
        reasoning_effort="medium",
    )

    assert gtk_command == tk_command


def test_ai_agent_launch_state_prefers_running_over_restore() -> None:
    state = ai_agent_launch_state(running=True, resumable=True)

    assert state.label_key == "ai_agent_running"
    assert state.reset_enabled


def test_ai_agent_launch_state_allows_reset_for_running_agent_without_resume() -> None:
    state = ai_agent_launch_state(running=True, resumable=False)

    assert state.label_key == "ai_agent_running"
    assert state.reset_enabled


def test_ai_agent_launch_state_reports_restore_only_when_resumable() -> None:
    restore_state = ai_agent_launch_state(running=False, resumable=True)
    new_state = ai_agent_launch_state(running=False, resumable=False)

    assert restore_state.label_key == "restore_ai_agent_session"
    assert restore_state.reset_enabled
    assert new_state.label_key == "run_ai_agent"
    assert not new_state.reset_enabled


def test_ai_agent_launch_state_for_selection_handles_missing_task(tmp_path: Path) -> None:
    state = ai_agent_launch_state_for_selection(
        None,
        tmp_path,
        "codex",
        running_agent="codex",
    )

    assert state.label_key == "run_ai_agent"
    assert not state.reset_enabled


def test_ai_agent_launch_state_for_selection_prefers_matching_running_agent(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    session_file = home / ".codex" / "sessions" / f"{session_id}.jsonl"
    session_file.parent.mkdir(parents=True)
    session_file.write_text("{}", encoding="utf-8")
    save_task_agent_session(summary, "codex", session_id=session_id)

    running_state = ai_agent_launch_state_for_selection(
        summary,
        tmp_path,
        "codex",
        running_agent="codex",
    )
    other_agent_state = ai_agent_launch_state_for_selection(
        summary,
        tmp_path,
        "codex",
        running_agent="claude",
    )

    assert running_state.label_key == "ai_agent_running"
    assert running_state.reset_enabled
    assert other_agent_state.label_key == "restore_ai_agent_session"
    assert other_agent_state.reset_enabled


def test_ai_agent_switch_decision_handles_no_current_agent() -> None:
    decision = ai_agent_switch_decision(
        "claude",
        current_agent=None,
        start_if_changed=True,
    )

    assert decision.action == "start_selected"
    assert decision.agent == "claude"
    assert decision.current_agent is None


def test_ai_agent_switch_decision_activates_matching_current_agent() -> None:
    decision = ai_agent_switch_decision(
        "codex",
        current_agent="codex",
        start_if_changed=True,
    )

    assert decision.action == "activate_current"
    assert decision.agent == "codex"
    assert decision.current_agent == "codex"


def test_ai_agent_switch_decision_keeps_current_when_selection_only() -> None:
    decision = ai_agent_switch_decision(
        "claude",
        current_agent="codex",
        start_if_changed=False,
    )

    assert decision.action == "keep_current"
    assert decision.agent == "codex"
    assert decision.current_agent == "codex"


def test_ai_agent_switch_decision_confirms_switch_when_starting_changed_agent() -> None:
    decision = ai_agent_switch_decision(
        "claude",
        current_agent="codex",
        start_if_changed=True,
    )

    assert decision.action == "confirm_switch"
    assert decision.agent == "claude"
    assert decision.current_agent == "codex"

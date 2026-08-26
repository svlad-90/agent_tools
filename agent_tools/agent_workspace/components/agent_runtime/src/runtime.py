from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from agent_tools.paf_workspace.task_check import check_task
from agent_tools.paf_workspace.task_check import render_text
from agent_tools.tools.task_context import agent_visible_slots as agent_visible_task_context_slots
from agent_tools.tools.task_context import load_slots as load_task_context_slots
from agent_tools.tools.task_context import render_slots as render_task_context_slots

from ...settings.api import AGENT_WORKSPACE_AGENTS
from ...settings.api import AGENT_WORKSPACE_DEFAULT_CLAUDE_PERMISSION_MODE
from ...settings.api import AGENT_WORKSPACE_DEFAULT_LIMITED_BASH_OUTPUT_TOKENS
from ...settings.api import AgentModelSettings
from ...settings.api import TASK_CONTEXT_PROMPT_INJECTION_DEFAULT
from ...settings.api import ai_agent_model_settings
from ...settings.api import normalize_agent
from ...task_sessions.api import AgentSessionState
from ...task_sessions.api import prepare_task_agent_session
from ...task_sessions.api import task_agent_has_saved_resumable_state
from ...harness_adapter.api import claude_harness_settings
from ...harness_adapter.api import CodexHarnessEvent


@dataclass(frozen=True)
class AgentLaunchCommand:
    command: list[str]
    session_state: AgentSessionState
    model_settings: AgentModelSettings


@dataclass(frozen=True)
class AgentLaunchState:
    label_key: str
    reset_enabled: bool


@dataclass(frozen=True)
class AgentSwitchDecision:
    action: str
    agent: str
    current_agent: str | None = None


def append_ai_agent_model_options(
    command: list[str],
    agent: str,
    *,
    model: str = "",
    reasoning_effort: str = "",
) -> None:
    model = model.strip()
    reasoning_effort = reasoning_effort.strip()
    if model:
        command.extend(["--model", model])
    if not reasoning_effort:
        return
    if normalize_agent(agent) == "claude":
        command.extend(["--effort", reasoning_effort])
    else:
        command.extend(["-c", f'model_reasoning_effort="{reasoning_effort}"'])


def append_ai_agent_permission_options(command: list[str], agent: str) -> None:
    if normalize_agent(agent) == "claude":
        command.extend(["--permission-mode", AGENT_WORKSPACE_DEFAULT_CLAUDE_PERMISSION_MODE])


def append_ai_agent_hook_options(command: list[str], agent: str, *, animations_enabled: bool = False) -> None:
    agent = normalize_agent(agent)
    if agent == "claude":
        settings = claude_harness_settings("python3 -m agent_tools.agent_workspace.components.harness_adapter.claude")
        settings["prefersReducedMotion"] = not animations_enabled
        command.extend(["--settings", json.dumps(settings, ensure_ascii=False)])
        return
    command.append("--dangerously-bypass-hook-trust")
    hook_command = "python3 -m agent_tools.agent_workspace.components.harness_adapter.codex"
    for event in CodexHarnessEvent:
        if event is CodexHarnessEvent.ALL:
            continue
        command.extend(
            [
                "-c",
                f'hooks.{event.value}=[{{hooks=[{{type="command",command="{hook_command}"}}]}}]',
            ]
            )


def append_codex_low_redraw_tui_options(command: list[str], *, animations_enabled: bool = False) -> None:
    if not animations_enabled:
        command.extend(["-c", "tui.animations=false"])
    command.extend(["-c", "tui.disable_mouse_capture=true"])


def build_ai_agent_console_command(
    workspace: Path,
    prompt: str,
    agent: str,
    *,
    codex_executable: str,
    claude_executable: str,
    resume: bool = False,
    resume_session_id: str | None = None,
    model: str = "",
    reasoning_effort: str = "",
    codex_animations_enabled: bool = False,
    claude_animations_enabled: bool = False,
) -> list[str]:
    agent = normalize_agent(agent)
    if agent == "claude":
        command = [claude_executable]
        append_ai_agent_permission_options(command, agent)
        append_ai_agent_model_options(command, agent, model=model, reasoning_effort=reasoning_effort)
        append_ai_agent_hook_options(command, agent, animations_enabled=claude_animations_enabled)
        if resume and resume_session_id:
            command.extend(["--resume", resume_session_id])
        else:
            if resume_session_id:
                command.extend(["--session-id", resume_session_id])
            command.append(prompt)
        return command

    command = [codex_executable]
    append_ai_agent_model_options(command, agent, model=model, reasoning_effort=reasoning_effort)
    append_ai_agent_hook_options(command, agent)
    append_codex_low_redraw_tui_options(command, animations_enabled=codex_animations_enabled)
    if resume and resume_session_id:
        command.extend(["resume", "--cd", str(workspace), "--no-alt-screen"])
        command.append(resume_session_id)
        return command
    command.extend(["--cd", str(workspace), "--no-alt-screen", prompt])
    return command


def ai_agent_task_context_prompt(
    task: Any,
    workspace: Path,
    suffix: str = "",
    *,
    inject_task_context: bool = TASK_CONTEXT_PROMPT_INJECTION_DEFAULT,
    system_prompt: str = "",
) -> str:
    _ = inject_task_context
    message = (
        f"We are working in workspace task `{task.name}`. "
        f"Workspace: {workspace}. "
        f"Task directory: {task.path}. "
        "Workspace policy is delivered by harness hooks. Task context source "
        "is TASK_CONTEXT.sqlite3 slots; query it when task state is needed. "
        "Use workspace rules for the rest of the workflow."
    )
    if suffix:
        message = f"{message} {suffix}"
    system_prompt = system_prompt.strip()
    if not system_prompt:
        return message
    return f"{message}\n\nWorkspace system prompt:\n\n{system_prompt}"


def active_task_context_prompt(task: Any) -> str:
    command = (
        "python3 -m agent_tools.tools.task_context query --task "
        f"{task.path} --format agent"
    )
    try:
        rendered = render_task_context_slots(
            agent_visible_task_context_slots(load_task_context_slots(task.path)),
            format_name="agent",
            task_dir=task.path,
        )
    except (OSError, ValueError) as exc:
        rendered = f"Task context query failed: {exc}"
    return (
        "Current task context slots preloaded from `TASK_CONTEXT.sqlite3`.\n\n"
        f"Command result of `{command}`:\n\n"
        f"{rendered.rstrip()}"
    )


def task_check_prompt_suffix(task: Any, workspace: Path) -> str:
    checks = check_task(task.path, workspace=workspace.resolve())
    report = render_text(task.path, checks, errors_only=True)
    if "FAIL " not in report:
        return ""
    return (
        "Task check reported errors before this AI session. Resolve these task "
        "workflow errors before implementing the requested change:\n"
        f"{report}"
    )


def prepare_ai_agent_launch_command(
    task: Any,
    workspace: Path,
    agent: str,
    *,
    codex_model: str,
    codex_reasoning: str,
    claude_model: str,
    claude_effort: str,
    codex_executable: str,
    claude_executable: str,
    prompt_suffix: str = "",
    include_task_check: bool = False,
    inject_task_context: bool = TASK_CONTEXT_PROMPT_INJECTION_DEFAULT,
    system_prompt: str = "",
    codex_animations_enabled: bool = False,
    claude_animations_enabled: bool = False,
) -> AgentLaunchCommand:
    agent = normalize_agent(agent)
    session_state = prepare_task_agent_session(task, workspace, agent)
    model_settings = ai_agent_model_settings(
        agent,
        codex_model=codex_model,
        codex_reasoning=codex_reasoning,
        claude_model=claude_model,
        claude_effort=claude_effort,
    )
    _ = include_task_check
    prompt = ai_agent_task_context_prompt(
        task,
        workspace,
        prompt_suffix,
        inject_task_context=inject_task_context,
        system_prompt=system_prompt,
    )
    return AgentLaunchCommand(
        command=build_ai_agent_console_command(
            workspace,
            prompt,
            agent,
            codex_executable=codex_executable,
            claude_executable=claude_executable,
            resume=session_state.resume,
            resume_session_id=session_state.session_id,
            model=model_settings.model,
            reasoning_effort=model_settings.reasoning_effort,
            codex_animations_enabled=codex_animations_enabled,
            claude_animations_enabled=claude_animations_enabled,
        ),
        session_state=session_state,
        model_settings=model_settings,
    )


def ai_agent_environment(
    base_env: dict[str, str],
    task: Any,
    workspace: Path,
    agent: str,
    session_state: AgentSessionState,
    *,
    run_id: str | None = None,
    limited_bash_output_tokens: int = AGENT_WORKSPACE_DEFAULT_LIMITED_BASH_OUTPUT_TOKENS,
) -> dict[str, str]:
    env = dict(base_env)
    agent = normalize_agent(agent)
    session_id = session_state.session_id or run_id or f"{agent}-default"
    env["AGENT_TOOLS_AGENT"] = agent
    env["AGENT_TOOLS_SESSION_ID"] = session_id
    env["AGENT_TOOLS_TASK_DIR"] = str(task.path)
    env["AGENT_TOOLS_WORKSPACE"] = str(workspace)
    env["AGENT_TOOLS_LIMITED_BASH_OUTPUT_TOKENS"] = str(limited_bash_output_tokens)
    if session_state.session_id:
        env["AGENT_TOOLS_AGENT_SESSION_ID"] = session_state.session_id
    if run_id:
        env["AGENT_TOOLS_RUN_ID"] = run_id
    return env


def ai_agent_launch_state(*, running: bool, resumable: bool) -> AgentLaunchState:
    if running:
        return AgentLaunchState(label_key="ai_agent_running", reset_enabled=True)
    if resumable:
        return AgentLaunchState(label_key="restore_ai_agent_session", reset_enabled=True)
    return AgentLaunchState(label_key="run_ai_agent", reset_enabled=False)


def ai_agent_launch_state_for_selection(
    task: Any | None,
    workspace: Path,
    agent: str,
    *,
    running_agent: str | None,
) -> AgentLaunchState:
    if task is None:
        return ai_agent_launch_state(running=False, resumable=False)
    agent = normalize_agent(agent)
    running = running_agent == agent
    resumable = task_agent_has_saved_resumable_state(task, agent)
    return ai_agent_launch_state(running=running, resumable=resumable)


def ai_agent_switch_decision(
    agent: str,
    *,
    current_agent: str | None,
    start_if_changed: bool,
) -> AgentSwitchDecision:
    agent = normalize_agent(agent)
    if current_agent is None:
        return AgentSwitchDecision(action="start_selected", agent=agent)
    current_agent = normalize_agent(current_agent)
    if current_agent == agent:
        return AgentSwitchDecision(
            action="activate_current",
            agent=agent,
            current_agent=current_agent,
        )
    if not start_if_changed:
        return AgentSwitchDecision(
            action="keep_current",
            agent=current_agent,
            current_agent=current_agent,
        )
    return AgentSwitchDecision(
        action="confirm_switch",
        agent=agent,
        current_agent=current_agent,
    )


def session_kind_is_agent(session_kind: str) -> bool:
    return session_kind in AGENT_WORKSPACE_AGENTS

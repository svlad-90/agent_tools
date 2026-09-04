from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

from ...task_catalog.api import TaskSummary


TASK_ACTIONS_FILE = "TASK_ACTIONS.json"
PAF_HIDE_TASK_ENV_VAR = "PAF_HIDE_TASK_ENV"
TASK_ACTION_LOGS_DIR = Path("report") / "logs"


@dataclass(frozen=True)
class TaskActionParameter:
    name: str
    label: str
    parameter_type: str
    set_name: str
    default: str
    global_name: str | None = None


@dataclass(frozen=True)
class TaskAction:
    action_id: str
    label: str
    command: str | tuple[str, ...]
    cwd: Path
    env: dict[str, str]
    parameters: tuple[TaskActionParameter, ...] = ()
    bindings: dict[str, str] | None = None
    base_action_id: str | None = None
    is_shortcut: bool = False
    source: str = "task"
    description: str = ""


@dataclass(frozen=True)
class TaskActionsConfig:
    actions: list[TaskAction]
    base_actions: list[TaskAction]
    parameter_sets: dict[str, dict[str, dict[str, str]]]
    global_parameter_bindings: dict[str, str]
    errors: list[str]


def load_task_actions(task: TaskSummary) -> tuple[list[TaskAction], list[str]]:
    config = load_task_actions_config(task)
    return config.actions, config.errors


def load_task_actions_config(task: TaskSummary) -> TaskActionsConfig:
    path = task.path / TASK_ACTIONS_FILE
    workspace_actions = workspace_standard_task_actions(task)
    if not path.is_file():
        return TaskActionsConfig(workspace_actions, workspace_actions, {}, {}, [])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return TaskActionsConfig(
            workspace_actions,
            workspace_actions,
            {},
            {},
            [f"{TASK_ACTIONS_FILE}: {error}"],
        )

    entries = data.get("actions") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return TaskActionsConfig(
            workspace_actions,
            workspace_actions,
            {},
            {},
            [f"{TASK_ACTIONS_FILE}: expected object with actions list"],
        )

    parameter_sets, parameter_errors = _parse_parameter_sets(data.get("parameter_sets", {}))
    parameter_types, parameter_type_errors = _parse_parameter_types(data.get("parameter_types", {}))
    global_bindings, global_errors = _parse_global_parameter_bindings(data.get("global_parameters", {}))
    actions_by_id: dict[str, TaskAction] = {}
    base_actions: list[TaskAction] = []
    launch_actions: list[TaskAction] = []
    errors: list[str] = []
    errors.extend(parameter_errors)
    errors.extend(parameter_type_errors)
    errors.extend(global_errors)
    seen: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        action, error = _parse_task_action(task, entry, index, parameter_types)
        if error is not None:
            errors.append(error)
            continue
        if action.action_id in seen:
            errors.append(f"{TASK_ACTIONS_FILE}: duplicate action id {action.action_id!r}")
            continue
        seen.add(action.action_id)
        base_actions.append(action)
        actions_by_id[action.action_id] = action
        launch_actions.append(
            bind_task_action_parameters(action, parameter_sets, action.bindings or {}, global_bindings)
        )

    shortcuts = data.get("shortcuts", []) if isinstance(data, dict) else []
    if shortcuts is not None and not isinstance(shortcuts, list):
        errors.append(f"{TASK_ACTIONS_FILE}: shortcuts must be a list")
        shortcuts = []
    shortcut_seen: set[str] = set()
    for index, entry in enumerate(shortcuts, start=1):
        shortcut, error = _parse_task_shortcut(entry, index, actions_by_id, parameter_sets, global_bindings)
        if error is not None:
            errors.append(error)
            continue
        if shortcut.action_id in seen or shortcut.action_id in shortcut_seen:
            errors.append(f"{TASK_ACTIONS_FILE}: duplicate shortcut id {shortcut.action_id!r}")
            continue
        shortcut_seen.add(shortcut.action_id)
        launch_actions.append(shortcut)
    return TaskActionsConfig(
        [*workspace_actions, *launch_actions],
        [*workspace_actions, *base_actions],
        parameter_sets,
        global_bindings,
        errors,
    )


def bind_task_action_parameters(
    action: TaskAction,
    parameter_sets: dict[str, dict[str, dict[str, str]]],
    bindings: dict[str, str],
    global_bindings: dict[str, str] | None = None,
) -> TaskAction:
    effective_bindings: dict[str, str] = {}
    env = dict(action.env)
    for parameter in action.parameters:
        selected = ""
        if parameter.global_name and global_bindings is not None:
            selected = global_bindings.get(parameter.global_name, "")
        if not selected:
            selected = bindings.get(parameter.name) or parameter.default
        effective_bindings[parameter.name] = selected
        _add_parameter_env(env, parameter, selected, parameter_sets)
    return TaskAction(
        action_id=action.action_id,
        label=action.label,
        command=action.command,
        cwd=action.cwd,
        env=env,
        description=action.description,
        parameters=action.parameters,
        bindings=effective_bindings,
        base_action_id=action.base_action_id,
        is_shortcut=action.is_shortcut,
        source=action.source,
    )


def workspace_standard_task_actions(task: TaskSummary) -> list[TaskAction]:
    workspace = _workspace_for_task(task.path)
    return [
        TaskAction(
            action_id="workspace:validate",
            label="Validate",
            command=(
                "python3",
                "-m",
                "agent_tools.tools.repo_guard",
                "validate",
                "--repo",
                str(workspace),
                "--task-dir",
                str(task.path),
            ),
            cwd=workspace,
            env={},
            description="Run workspace and repository policy checks for the workspace repository.",
            source="workspace",
        ),
        TaskAction(
            action_id="workspace:validate-push",
            label="Validate push",
            command=(
                "python3",
                "-m",
                "agent_tools.tools.repo_guard",
                "pre-push-dry-run",
                "--repo",
                str(workspace),
                "--remote",
                "origin",
                "--task-dir",
                str(task.path),
            ),
            cwd=workspace,
            env={},
            description=(
                "Dry-run pre-push policy checks and install/update hooks for repositories "
                "listed in the task repo-registry."
            ),
            source="workspace",
        ),
        TaskAction(
            action_id="workspace:task-check",
            label="Task check",
            command=(
                "python3",
                "-m",
                "agent_tools.agent_workspace.actions",
                "task-check",
                "--workspace",
                str(workspace),
                "--task",
                str(task.path),
                "--issues-only",
            ),
            cwd=workspace,
            env={},
            description="Run task_check and print only warnings and errors that need action.",
            source="workspace",
        ),
        TaskAction(
            action_id="workspace:install-repo-hooks",
            label="Install/update repo hooks",
            command=(
                "python3",
                "-m",
                "agent_tools.paf_workspace.task_check",
                str(task.path),
                "--workspace",
                str(workspace),
                "--install-repo-hooks",
                "--issues-only",
            ),
            cwd=workspace,
            env={},
            description=(
                "Install or update push hooks for git repository roots listed in the task "
                "repo-registry, then print task_check issues that still need action."
            ),
            source="workspace",
        ),
    ]


def load_task_actions_data(task: TaskSummary) -> tuple[dict[str, Any], list[str]]:
    path = task.path / TASK_ACTIONS_FILE
    if not path.is_file():
        return {"actions": []}, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {}, [f"{TASK_ACTIONS_FILE}: {error}"]
    if not isinstance(data, dict):
        return {}, [f"{TASK_ACTIONS_FILE}: expected object"]
    return data, []


def save_task_actions_data(task: TaskSummary, data: dict[str, Any]) -> None:
    path = task.path / TASK_ACTIONS_FILE
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def run_task_action(action: TaskAction) -> str:
    env = os.environ.copy()
    env.update(action.env)
    env[PAF_HIDE_TASK_ENV_VAR] = "1"
    command = list(action.command) if isinstance(action.command, tuple) else action.command
    completed = subprocess.run(
        command,
        cwd=action.cwd,
        env=env,
        shell=isinstance(action.command, str),
        check=False,
        text=True,
        capture_output=True,
    )
    output = completed.stdout
    if completed.stderr:
        output += completed.stderr
    output += f"\nexit code: {completed.returncode}\n"
    return output


def task_action_log_basename(action_id: str) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", action_id).strip(".-")
    return safe_name or "task-action"


def _workspace_for_task(task_path: Path) -> Path:
    resolved = task_path.resolve()
    for parent in resolved.parents:
        if parent.name == "tasks":
            return parent.parent
    return resolved.parent


def _parse_task_action(
    task: TaskSummary,
    entry: object,
    index: int,
    parameter_types: dict[str, str],
) -> tuple[TaskAction, None] | tuple[None, str]:
    if not isinstance(entry, dict):
        return None, f"{TASK_ACTIONS_FILE}: action {index} must be an object"

    action_id = _string_field(entry, "id")
    label = _string_field(entry, "label")
    description = _string_field(entry, "description") or ""
    command = _command_field(entry.get("command"))
    if action_id is None:
        return None, f"{TASK_ACTIONS_FILE}: action {index} missing string id"
    if label is None:
        return None, f"{TASK_ACTIONS_FILE}: action {index} missing string label"
    if command is None:
        return None, f"{TASK_ACTIONS_FILE}: action {index} missing command"

    cwd_text = _string_field(entry, "cwd") or "."
    cwd = (task.path / cwd_text).resolve()
    try:
        cwd.relative_to(task.path.resolve())
    except ValueError:
        return None, f"{TASK_ACTIONS_FILE}: action {action_id!r} cwd escapes task"

    env_data = entry.get("env", {})
    if not isinstance(env_data, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in env_data.items()
    ):
        return None, f"{TASK_ACTIONS_FILE}: action {action_id!r} env must be string map"

    parameters, parameter_error = _parse_action_parameters(action_id, entry.get("parameters", []), parameter_types)
    if parameter_error is not None:
        return None, parameter_error

    return TaskAction(
        action_id=action_id,
        label=label,
        command=command,
        cwd=cwd,
        env=dict(env_data),
        description=description,
        parameters=parameters,
        bindings={parameter.name: parameter.default for parameter in parameters},
    ), None


def _parse_task_shortcut(
    entry: object,
    index: int,
    actions_by_id: dict[str, TaskAction],
    parameter_sets: dict[str, dict[str, dict[str, str]]],
    global_bindings: dict[str, str],
) -> tuple[TaskAction, None] | tuple[None, str]:
    if not isinstance(entry, dict):
        return None, f"{TASK_ACTIONS_FILE}: shortcut {index} must be an object"
    shortcut_id = _string_field(entry, "id")
    label = _string_field(entry, "label")
    action_id = _string_field(entry, "action")
    if shortcut_id is None:
        return None, f"{TASK_ACTIONS_FILE}: shortcut {index} missing string id"
    if label is None:
        return None, f"{TASK_ACTIONS_FILE}: shortcut {index} missing string label"
    if action_id is None:
        return None, f"{TASK_ACTIONS_FILE}: shortcut {shortcut_id!r} missing string action"
    base = actions_by_id.get(action_id)
    if base is None:
        return None, f"{TASK_ACTIONS_FILE}: shortcut {shortcut_id!r} references unknown action {action_id!r}"
    bindings = entry.get("bindings", {})
    if not isinstance(bindings, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in bindings.items()
    ):
        return None, f"{TASK_ACTIONS_FILE}: shortcut {shortcut_id!r} bindings must be string map"
    bound = bind_task_action_parameters(base, parameter_sets, dict(bindings), global_bindings)
    return TaskAction(
        action_id=shortcut_id,
        label=label,
        command=bound.command,
        cwd=bound.cwd,
        env=bound.env,
        description=base.description,
        parameters=bound.parameters,
        bindings=bound.bindings,
        base_action_id=base.action_id,
        is_shortcut=True,
    ), None


def _parse_action_parameters(
    action_id: str,
    entries: object,
    parameter_types: dict[str, str],
) -> tuple[tuple[TaskActionParameter, ...], str | None]:
    if entries in (None, []):
        return (), None
    if not isinstance(entries, list):
        return (), f"{TASK_ACTIONS_FILE}: action {action_id!r} parameters must be a list"
    parameters: list[TaskActionParameter] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            return (), f"{TASK_ACTIONS_FILE}: action {action_id!r} parameter {index} must be an object"
        name = _string_field(entry, "name")
        parameter_type = _string_field(entry, "type")
        if name is None:
            return (), f"{TASK_ACTIONS_FILE}: action {action_id!r} parameter {index} missing string name"
        if parameter_type is None:
            return (), f"{TASK_ACTIONS_FILE}: action {action_id!r} parameter {name!r} missing string type"
        set_name = parameter_types.get(parameter_type)
        if set_name is None:
            return (), f"{TASK_ACTIONS_FILE}: action {action_id!r} parameter {name!r} references unknown type {parameter_type!r}"
        if name in seen:
            return (), f"{TASK_ACTIONS_FILE}: action {action_id!r} duplicate parameter {name!r}"
        seen.add(name)
        label = _string_field(entry, "label") or name
        default = _string_field(entry, "default") or ""
        global_name = _string_field(entry, "global")
        parameters.append(
            TaskActionParameter(
                name=name,
                label=label,
                parameter_type=parameter_type,
                set_name=set_name,
                default=default,
                global_name=global_name,
            )
        )
    return tuple(parameters), None


def _parse_global_parameter_bindings(value: object) -> tuple[dict[str, str], list[str]]:
    if value in (None, {}):
        return {}, []
    if not isinstance(value, dict):
        return {}, [f"{TASK_ACTIONS_FILE}: global_parameters must be an object"]
    bindings: dict[str, str] = {}
    errors: list[str] = []
    for name, definition in value.items():
        if not isinstance(name, str):
            errors.append(f"{TASK_ACTIONS_FILE}: global parameter names must be strings")
            continue
        if isinstance(definition, str):
            bindings[name] = definition
            continue
        if not isinstance(definition, dict):
            errors.append(f"{TASK_ACTIONS_FILE}: global parameter {name!r} must be a string or object")
            continue
        selected = _string_field(definition, "value") or _string_field(definition, "default")
        if selected:
            bindings[name] = selected
    return bindings, errors


def _parse_parameter_types(value: object) -> tuple[dict[str, str], list[str]]:
    if value in (None, {}):
        return {}, []
    if not isinstance(value, dict):
        return {}, [f"{TASK_ACTIONS_FILE}: parameter_types must be an object"]
    parameter_types: dict[str, str] = {}
    errors: list[str] = []
    for type_name, definition in value.items():
        if not isinstance(type_name, str):
            errors.append(f"{TASK_ACTIONS_FILE}: parameter_types keys must be strings")
            continue
        if not isinstance(definition, dict):
            errors.append(f"{TASK_ACTIONS_FILE}: parameter type {type_name!r} must be an object")
            continue
        set_name = _string_field(definition, "set")
        if set_name is None:
            errors.append(f"{TASK_ACTIONS_FILE}: parameter type {type_name!r} missing string set")
            continue
        parameter_types[type_name] = set_name
    return parameter_types, errors


def _parse_parameter_sets(value: object) -> tuple[dict[str, dict[str, dict[str, str]]], list[str]]:
    if value in (None, {}):
        return {}, []
    if not isinstance(value, dict):
        return {}, [f"{TASK_ACTIONS_FILE}: parameter_sets must be an object"]
    parameter_sets: dict[str, dict[str, dict[str, str]]] = {}
    errors: list[str] = []
    for set_name, entries in value.items():
        if not isinstance(set_name, str) or not isinstance(entries, dict):
            errors.append(f"{TASK_ACTIONS_FILE}: parameter set names and values must be objects")
            continue
        set_entries: dict[str, dict[str, str]] = {}
        for entry_name, fields in entries.items():
            if not isinstance(entry_name, str) or not isinstance(fields, dict):
                errors.append(f"{TASK_ACTIONS_FILE}: parameter set {set_name!r} entries must be objects")
                continue
            set_entries[entry_name] = {
                str(key): str(field_value)
                for key, field_value in fields.items()
                if isinstance(key, str) and isinstance(field_value, (str, int, float, bool))
            }
        parameter_sets[set_name] = set_entries
    return parameter_sets, errors


def _add_parameter_env(
    env: dict[str, str],
    parameter: TaskActionParameter,
    selected: str,
    parameter_sets: dict[str, dict[str, dict[str, str]]],
) -> None:
    parameter_key = _env_key(parameter.name)
    env[f"TASK_ACTION_PARAM_{parameter_key}"] = selected
    values = parameter_sets.get(parameter.set_name, {}).get(selected, {})
    for field, value in values.items():
        env[f"TASK_ACTION_PARAM_{parameter_key}_{_env_key(field)}"] = value


def _env_key(value: str) -> str:
    key = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    return key or "VALUE"


def _string_field(entry: dict[str, Any], name: str) -> str | None:
    value = entry.get(name)
    return value if isinstance(value, str) and value else None


def _command_field(value: object) -> str | tuple[str, ...] | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, list) and value and all(isinstance(item, str) for item in value):
        return tuple(value)
    return None

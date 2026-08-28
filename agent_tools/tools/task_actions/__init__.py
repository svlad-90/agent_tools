from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys
from typing import Sequence

from agent_tools.agent_workspace.components.task_actions.api import PAF_HIDE_TASK_ENV_VAR
from agent_tools.agent_workspace.components.task_actions.api import TaskAction
from agent_tools.agent_workspace.components.task_actions.api import bind_task_action_parameters
from agent_tools.agent_workspace.components.task_actions.api import load_task_actions_config
from agent_tools.agent_workspace.components.task_actions.api import load_task_actions_data
from agent_tools.agent_workspace.components.task_actions.api import save_task_actions_data
from agent_tools.agent_workspace.components.task_catalog.api import TaskSummary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect and run task-declared actions.")
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    list_parser = subparsers.add_parser("list", help="List task actions.")
    list_parser.add_argument("--task", required=True, help="Task directory.")
    list_parser.add_argument("--json", action="store_true", help="Render JSON.")
    list_parser.set_defaults(func=_main_list)

    show_parser = subparsers.add_parser("show", help="Show one task action.")
    show_parser.add_argument("--task", required=True, help="Task directory.")
    show_parser.add_argument("--action", required=True, help="Action id.")
    show_parser.add_argument("--json", action="store_true", help="Render JSON.")
    show_parser.set_defaults(func=_main_show)

    run_parser = subparsers.add_parser("run", help="Run one task action.")
    run_parser.add_argument("--task", required=True, help="Task directory.")
    run_parser.add_argument("--action", required=True, help="Action id.")
    run_parser.add_argument(
        "--binding",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="Override one action parameter binding. May be passed more than once.",
    )
    run_parser.add_argument("--json", action="store_true", help="Render JSON.")
    run_parser.set_defaults(func=_main_run)

    add_parser = subparsers.add_parser("add", help="Add one task action.")
    add_parser.add_argument("--task", required=True, help="Task directory.")
    add_parser.add_argument("--action", required=True, help="Action id.")
    add_parser.add_argument("--label", required=True, help="Action label.")
    _add_edit_arguments(add_parser, require_command=True)
    add_parser.add_argument("--json", action="store_true", help="Render JSON.")
    add_parser.set_defaults(func=_main_add)

    update_parser = subparsers.add_parser("update", help="Update one task action.")
    update_parser.add_argument("--task", required=True, help="Task directory.")
    update_parser.add_argument("--action", required=True, help="Action id.")
    update_parser.add_argument("--label", help="Action label.")
    _add_edit_arguments(update_parser, require_command=False)
    update_parser.add_argument("--json", action="store_true", help="Render JSON.")
    update_parser.set_defaults(func=_main_update)

    delete_parser = subparsers.add_parser("delete", help="Delete one task action.")
    delete_parser.add_argument("--task", required=True, help="Task directory.")
    delete_parser.add_argument("--action", required=True, help="Action id.")
    delete_parser.add_argument("--json", action="store_true", help="Render JSON.")
    delete_parser.set_defaults(func=_main_delete)

    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return int(args.func(args))
    except ValueError as error:
        print(f"task_actions: error: {error}", file=sys.stderr)
        return 1


def list_actions(task_dir: Path) -> dict[str, object]:
    task = _task_summary(task_dir)
    config = load_task_actions_config(task)
    return {
        "task": str(task.path),
        "actions": [_action_json(action) for action in config.actions],
        "base_actions": [_action_json(action) for action in config.base_actions],
        "parameter_sets": config.parameter_sets,
        "global_parameter_bindings": config.global_parameter_bindings,
        "errors": config.errors,
    }


def show_action(task_dir: Path, action_id: str) -> dict[str, object]:
    payload = list_actions(task_dir)
    action = _find_action(payload["actions"], action_id)
    if action is None:
        raise ValueError(f"task action not found: {action_id}")
    payload["action"] = action
    return payload


def run_action(
    task_dir: Path,
    action_id: str,
    bindings: dict[str, str] | None = None,
) -> dict[str, object]:
    task = _task_summary(task_dir)
    config = load_task_actions_config(task)
    action = _find_task_action(config.actions, action_id)
    if action is None:
        raise ValueError(f"task action not found: {action_id}")
    bound = bind_task_action_parameters(
        action,
        config.parameter_sets,
        bindings or {},
        config.global_parameter_bindings,
    )
    env = os.environ.copy()
    env.update(bound.env)
    env[PAF_HIDE_TASK_ENV_VAR] = "1"
    command = list(bound.command) if isinstance(bound.command, tuple) else bound.command
    completed = subprocess.run(
        command,
        cwd=bound.cwd,
        env=env,
        shell=isinstance(bound.command, str),
        check=False,
        text=True,
        capture_output=True,
    )
    return {
        "task": str(task.path),
        "action": _action_json(bound),
        "command": command,
        "cwd": str(bound.cwd),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "output": completed.stdout + completed.stderr,
        "errors": config.errors,
    }


def add_action(
    task_dir: Path,
    action_id: str,
    label: str,
    command: str | list[str],
    *,
    cwd: str = ".",
    env: dict[str, str] | None = None,
    parameters: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    task = _task_summary(task_dir)
    data, errors = load_task_actions_data(task)
    if errors:
        raise ValueError("; ".join(errors))
    actions = _actions_data(data)
    if _find_action(actions, action_id) is not None:
        raise ValueError(f"task action already exists: {action_id}")
    entry: dict[str, object] = {
        "id": action_id,
        "label": label,
        "command": command,
        "cwd": cwd,
    }
    if env:
        entry["env"] = dict(env)
    if parameters:
        entry["parameters"] = list(parameters)
    actions.append(entry)
    save_task_actions_data(task, data)
    return show_action(task_dir, action_id)


def update_action(
    task_dir: Path,
    action_id: str,
    *,
    label: str | None = None,
    command: str | list[str] | None = None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    parameters: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    task = _task_summary(task_dir)
    data, errors = load_task_actions_data(task)
    if errors:
        raise ValueError("; ".join(errors))
    action = _find_action(_actions_data(data), action_id)
    if action is None:
        raise ValueError(f"task action not found: {action_id}")
    if label is not None:
        action["label"] = label
    if command is not None:
        action["command"] = command
    if cwd is not None:
        action["cwd"] = cwd
    if env is not None:
        action["env"] = dict(env)
    if parameters is not None:
        action["parameters"] = list(parameters)
    save_task_actions_data(task, data)
    return show_action(task_dir, action_id)


def delete_action(task_dir: Path, action_id: str) -> dict[str, object]:
    task = _task_summary(task_dir)
    data, errors = load_task_actions_data(task)
    if errors:
        raise ValueError("; ".join(errors))
    actions = _actions_data(data)
    before = len(actions)
    data["actions"] = [
        entry for entry in actions if not (isinstance(entry, dict) and entry.get("id") == action_id)
    ]
    removed_actions = before - len(data["actions"])
    removed_shortcuts = _delete_shortcuts_for_action(data, action_id)
    if not removed_actions and not removed_shortcuts:
        raise ValueError(f"task action not found: {action_id}")
    save_task_actions_data(task, data)
    payload = list_actions(task_dir)
    payload["deleted"] = {
        "id": action_id,
        "actions": removed_actions,
        "shortcuts": removed_shortcuts,
    }
    return payload


def _main_list(args: argparse.Namespace) -> int:
    payload = list_actions(Path(args.task))
    _print_payload(payload, json_output=args.json)
    return 1 if payload["errors"] else 0


def _main_show(args: argparse.Namespace) -> int:
    payload = show_action(Path(args.task), args.action)
    _print_payload(payload["action"], json_output=args.json)
    return 0


def _main_run(args: argparse.Namespace) -> int:
    payload = run_action(Path(args.task), args.action, _parse_bindings(args.binding))
    _print_payload(payload, json_output=args.json)
    return int(payload["returncode"])


def _main_add(args: argparse.Namespace) -> int:
    payload = add_action(
        Path(args.task),
        args.action,
        args.label,
        _command_arg(args),
        cwd=args.cwd,
        env=_json_object_arg(args.env_json, "env-json"),
        parameters=_json_list_arg(args.parameters_json, "parameters-json"),
    )
    _print_payload(payload["action"], json_output=args.json)
    return 0


def _main_update(args: argparse.Namespace) -> int:
    payload = update_action(
        Path(args.task),
        args.action,
        label=args.label,
        command=_command_arg(args) if args.command or args.command_json else None,
        cwd=args.cwd,
        env=_json_object_arg(args.env_json, "env-json") if args.env_json else None,
        parameters=_json_list_arg(args.parameters_json, "parameters-json") if args.parameters_json else None,
    )
    _print_payload(payload["action"], json_output=args.json)
    return 0


def _main_delete(args: argparse.Namespace) -> int:
    payload = delete_action(Path(args.task), args.action)
    _print_payload(payload, json_output=args.json)
    return 0


def _task_summary(task_dir: Path) -> TaskSummary:
    task_dir = task_dir.expanduser().resolve()
    return TaskSummary(
        name=task_dir.name,
        path=task_dir,
        has_description=True,
        has_context=(task_dir / "TASK_CONTEXT.sqlite3").is_file(),
        description_tokens=0,
        context_tokens=0,
        context_over_budget=False,
    )


def _action_json(action: TaskAction) -> dict[str, object]:
    return {
        "id": action.action_id,
        "label": action.label,
        "command": list(action.command) if isinstance(action.command, tuple) else action.command,
        "cwd": str(action.cwd),
        "env": dict(action.env),
        "parameters": [asdict(parameter) for parameter in action.parameters],
        "bindings": dict(action.bindings or {}),
        "base_action_id": action.base_action_id,
        "is_shortcut": action.is_shortcut,
    }


def _find_action(actions: object, action_id: str) -> dict[str, object] | None:
    if not isinstance(actions, list):
        return None
    for action in actions:
        if isinstance(action, dict) and action.get("id") == action_id:
            return action
    return None


def _actions_data(data: dict[str, object]) -> list[object]:
    actions = data.setdefault("actions", [])
    if not isinstance(actions, list):
        raise ValueError("TASK_ACTIONS.json: actions must be a list")
    return actions


def _delete_shortcuts_for_action(data: dict[str, object], action_id: str) -> int:
    shortcuts = data.get("shortcuts")
    if not isinstance(shortcuts, list):
        return 0
    filtered = [
        entry
        for entry in shortcuts
        if not (
            isinstance(entry, dict)
            and (entry.get("id") == action_id or entry.get("action") == action_id)
        )
    ]
    removed = len(shortcuts) - len(filtered)
    if removed:
        data["shortcuts"] = filtered
    return removed


def _find_task_action(actions: list[TaskAction], action_id: str) -> TaskAction | None:
    for action in actions:
        if action.action_id == action_id:
            return action
    return None


def _parse_bindings(values: list[str]) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"binding must be NAME=VALUE: {value}")
        name, binding = value.split("=", 1)
        if not name:
            raise ValueError(f"binding name must not be empty: {value}")
        bindings[name] = binding
    return bindings


def _add_edit_arguments(parser: argparse.ArgumentParser, *, require_command: bool) -> None:
    command_group = parser.add_mutually_exclusive_group(required=require_command)
    command_group.add_argument("--command", help="Shell command string.")
    command_group.add_argument("--command-json", help="JSON string or string list command.")
    parser.add_argument("--cwd", default=".", help="Action working directory relative to task.")
    parser.add_argument("--env-json", help="JSON string map for action environment.")
    parser.add_argument("--parameters-json", help="JSON list for action parameters.")


def _command_arg(args: argparse.Namespace) -> str | list[str]:
    if args.command is not None:
        return str(args.command)
    value = json.loads(args.command_json)
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise ValueError("command-json must be a string or a list of strings")


def _json_object_arg(value: str | None, name: str) -> dict[str, str] | None:
    if value is None:
        return None
    parsed = json.loads(value)
    if not isinstance(parsed, dict) or not all(
        isinstance(key, str) and isinstance(item, str)
        for key, item in parsed.items()
    ):
        raise ValueError(f"{name} must be a string map")
    return dict(parsed)


def _json_list_arg(value: str | None, name: str) -> list[dict[str, object]] | None:
    if value is None:
        return None
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
        raise ValueError(f"{name} must be a list of objects")
    return [dict(item) for item in parsed]


def _print_payload(payload: object, *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if isinstance(payload, dict) and isinstance(payload.get("actions"), list):
        for action in payload["actions"]:
            if isinstance(action, dict):
                print(f"{action.get('id')}\t{action.get('label')}")
        for error in payload.get("errors", []):
            print(f"error: {error}", file=sys.stderr)
        return
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))

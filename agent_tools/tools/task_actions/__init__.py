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

    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


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

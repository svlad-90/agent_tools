from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def task_reorder_label_key(reorder_mode: bool) -> str:
    return "action.stop_reorder_actions" if reorder_mode else "action.reorder_actions"


@dataclass(frozen=True)
class TaskParameterMenuState:
    selected_value: str
    reorder_label_key: str


def task_parameter_menu_state(selected_value: str, reorder_mode: bool) -> TaskParameterMenuState:
    return TaskParameterMenuState(
        selected_value=selected_value,
        reorder_label_key=task_reorder_label_key(reorder_mode),
    )


@dataclass(frozen=True)
class TaskActionMenuState:
    actions_file: Path | None
    code_path: Path | None
    reorder_label_key: str


def task_action_menu_state(
    task_path: Path | None,
    code_path: Path | None,
    reorder_mode: bool,
) -> TaskActionMenuState:
    return TaskActionMenuState(
        actions_file=task_path / "TASK_ACTIONS.json" if task_path is not None else None,
        code_path=code_path,
        reorder_label_key=task_reorder_label_key(reorder_mode),
    )


@dataclass(frozen=True)
class TaskShortcutMenuState:
    reorder_label_key: str


def task_shortcut_menu_state(reorder_mode: bool) -> TaskShortcutMenuState:
    return TaskShortcutMenuState(reorder_label_key=task_reorder_label_key(reorder_mode))

from __future__ import annotations

from .actions import TaskAction
from .actions import TaskActionParameter
from .actions import TaskActionsConfig


def shortcuts_for_action(action: TaskAction, shortcuts: list[TaskAction]) -> list[TaskAction]:
    base_action_id = action.base_action_id or action.action_id
    return [shortcut for shortcut in shortcuts if shortcut.base_action_id == base_action_id]


def selected_parameter_value(
    parameter: TaskActionParameter,
    bindings: dict[str, str],
    global_bindings: dict[str, str],
) -> str:
    if parameter.global_name:
        selected = global_bindings.get(parameter.global_name)
        if selected:
            return selected
    return bindings.get(parameter.name) or parameter.default


def parameter_values(
    parameter: TaskActionParameter,
    config: TaskActionsConfig | None,
) -> dict[str, dict[str, str]]:
    if config is None:
        return {}
    return config.parameter_sets.get(parameter.set_name, {})


def parameter_button_label(
    parameter: TaskActionParameter,
    config: TaskActionsConfig | None,
    bindings: dict[str, str],
) -> str:
    global_bindings = config.global_parameter_bindings if config is not None else {}
    selected = selected_parameter_value(parameter, bindings, global_bindings)
    values = parameter_values(parameter, config)
    label = values.get(selected, {}).get("name") or values.get(selected, {}).get("label", selected)
    return f"{parameter.label}: {label}"


def bindings_for_action_run(
    action: TaskAction,
    selected_action_id: str | None,
    selected_bindings: dict[str, str],
) -> dict[str, str]:
    if selected_action_id == action.action_id:
        return selected_bindings
    return dict(action.bindings or {})

from __future__ import annotations


def shortcut_id_from_label(label: str) -> str:
    value = label.strip().lower()
    value = "".join(character if character.isalnum() else "-" for character in value)
    value = "-".join(part for part in value.split("-") if part)
    return value or "shortcut"


def parameter_value_id_from_name(name: str) -> str:
    value = name.strip().lower()
    value = "".join(character if character.isalnum() else "_" for character in value)
    value = "_".join(part for part in value.split("_") if part)
    return value or "value"


def unique_parameter_value_id(candidate: str, existing: dict[object, object]) -> str:
    if candidate not in existing:
        return candidate
    index = 2
    while f"{candidate}_{index}" in existing:
        index += 1
    return f"{candidate}_{index}"


def upsert_parameter_set_value(
    data: dict[str, object],
    set_name: str,
    value_id: str | None,
    candidate_id: str,
    value: dict[str, str],
) -> str | None:
    parameter_sets = data.setdefault("parameter_sets", {})
    if not isinstance(parameter_sets, dict):
        return None
    set_values = parameter_sets.setdefault(set_name, {})
    if not isinstance(set_values, dict):
        return None
    new_id = candidate_id
    if value_id != new_id:
        new_id = unique_parameter_value_id(new_id, set_values)
    if value_id and value_id != new_id:
        set_values.pop(value_id, None)
    set_values[new_id] = value
    return new_id


def delete_parameter_set_value(data: dict[str, object], set_name: str, value_id: str) -> bool:
    parameter_sets = data.get("parameter_sets")
    if not isinstance(parameter_sets, dict):
        return False
    set_values = parameter_sets.get(set_name)
    if not isinstance(set_values, dict) or value_id not in set_values:
        return False
    set_values.pop(value_id, None)
    return True


def move_json_list_entry(entries: list[object], key_name: str, entry_id: str, offset: int) -> bool:
    if offset == 0:
        return False
    for index, entry in enumerate(entries):
        if isinstance(entry, dict) and entry.get(key_name) == entry_id:
            new_index = index + offset
            if new_index < 0 or new_index >= len(entries):
                return False
            entries[index], entries[new_index] = entries[new_index], entries[index]
            return True
    return False


def move_json_mapping_entry(mapping: dict[object, object], entry_id: str, offset: int) -> bool:
    if offset == 0 or entry_id not in mapping:
        return False
    items = list(mapping.items())
    index = next((idx for idx, (key, _value) in enumerate(items) if key == entry_id), -1)
    new_index = index + offset
    if index < 0 or new_index < 0 or new_index >= len(items):
        return False
    items[index], items[new_index] = items[new_index], items[index]
    mapping.clear()
    mapping.update(items)
    return True


def move_json_list_entry_before(entries: list[object], key_name: str, entry_id: str, before_id: str) -> bool:
    if entry_id == before_id:
        return False
    source_index = json_list_entry_index(entries, key_name, entry_id)
    target_index = json_list_entry_index(entries, key_name, before_id)
    if source_index < 0 or target_index < 0:
        return False
    entry = entries.pop(source_index)
    if source_index < target_index:
        target_index -= 1
    entries.insert(target_index, entry)
    return True


def move_id_before(entries: list[str], entry_id: str, before_id: str) -> bool:
    return move_id_relative(entries, entry_id, before_id, after=False)


def move_id_relative(entries: list[str], entry_id: str, target_id: str, *, after: bool) -> bool:
    if entry_id == target_id:
        return False
    original = list(entries)
    try:
        source_index = entries.index(entry_id)
        target_index = entries.index(target_id)
    except ValueError:
        return False
    value = entries.pop(source_index)
    if source_index < target_index:
        target_index -= 1
    if after:
        target_index += 1
    entries.insert(target_index, value)
    return entries != original


def task_reorder_order_for_drag_edges(
    order: list[str],
    source_id: str,
    target_centers: dict[str, float],
    *,
    dragged_left: float,
    dragged_right: float,
    moving_right: bool,
) -> list[str] | None:
    try:
        current_slot = order.index(source_id)
    except ValueError:
        return None
    remaining = [item_id for item_id in order if item_id != source_id]
    if moving_right:
        next_slot = sum(1 for item_id in remaining if target_centers.get(item_id, float("inf")) <= dragged_right)
        if next_slot <= current_slot:
            return None
    else:
        next_slot = sum(1 for item_id in remaining if target_centers.get(item_id, float("inf")) < dragged_left)
        if next_slot >= current_slot:
            return None
    next_slot = max(0, min(next_slot, len(remaining)))
    new_order = list(remaining)
    new_order.insert(next_slot, source_id)
    return new_order if new_order != order else None


def reorder_json_list_by_ids(entries: list[object], key_name: str, ordered_ids: list[str]) -> bool:
    order = {entry_id: position for position, entry_id in enumerate(ordered_ids)}
    indexed_entries = list(enumerate(entries))
    reordered = sorted(
        indexed_entries,
        key=lambda item: (
            order.get(item[1].get(key_name), len(order)) if isinstance(item[1], dict) else len(order),
            item[0],
        ),
    )
    new_entries = [entry for _index, entry in reordered]
    if new_entries == entries:
        return False
    entries[:] = new_entries
    return True


def reorder_json_list_subset_by_ids(entries: list[object], key_name: str, ordered_ids: list[str]) -> bool:
    visible_ids = set(ordered_ids)
    ordered_visible = [
        entry
        for entry in sorted(
            [entry for entry in entries if isinstance(entry, dict) and entry.get(key_name) in visible_ids],
            key=lambda entry: ordered_ids.index(entry.get(key_name)),
        )
    ]
    if not ordered_visible:
        return False
    visible_iter = iter(ordered_visible)
    new_entries: list[object] = []
    for entry in entries:
        if isinstance(entry, dict) and entry.get(key_name) in visible_ids:
            new_entries.append(next(visible_iter))
        else:
            new_entries.append(entry)
    if new_entries == entries:
        return False
    entries[:] = new_entries
    return True


def reorder_json_mapping_by_ids(mapping: dict[object, object], ordered_ids: list[str]) -> bool:
    order = {entry_id: position for position, entry_id in enumerate(ordered_ids)}
    items = list(mapping.items())
    indexed_items = list(enumerate(items))
    reordered = [
        item
        for _index, item in sorted(indexed_items, key=lambda indexed: (order.get(indexed[1][0], len(order)), indexed[0]))
    ]
    if reordered == items:
        return False
    mapping.clear()
    mapping.update(reordered)
    return True


def json_list_entry_index(entries: list[object], key_name: str, entry_id: str) -> int:
    for index, entry in enumerate(entries):
        if isinstance(entry, dict) and entry.get(key_name) == entry_id:
            return index
    return -1


def move_action_parameter_entry(data: dict[str, object], action_id: str, parameter_name: str, offset: int) -> bool:
    actions = data.get("actions")
    if not isinstance(actions, list):
        return False
    for action in actions:
        if not isinstance(action, dict) or action.get("id") != action_id:
            continue
        parameters = action.get("parameters")
        if not isinstance(parameters, list):
            return False
        return move_json_list_entry(parameters, "name", parameter_name, offset)
    return False


def reorder_action_parameter_entries(data: dict[str, object], action_id: str, ordered_names: list[str]) -> bool:
    actions = data.get("actions")
    if not isinstance(actions, list):
        return False
    for action in actions:
        if not isinstance(action, dict) or action.get("id") != action_id:
            continue
        parameters = action.get("parameters")
        if not isinstance(parameters, list):
            return False
        return reorder_json_list_by_ids(parameters, "name", ordered_names)
    return False


def reorder_task_action_data(
    data: dict[str, object],
    group: str,
    ordered_ids: list[str],
    *,
    selected_action_id: str | None = None,
) -> bool:
    if group == "action":
        actions = data.get("actions")
        return isinstance(actions, list) and reorder_json_list_by_ids(actions, "id", ordered_ids)
    if group == "shortcut":
        shortcuts = data.get("shortcuts")
        return isinstance(shortcuts, list) and reorder_json_list_subset_by_ids(shortcuts, "id", ordered_ids)
    if group == "parameter":
        if selected_action_id is None:
            return False
        return reorder_action_parameter_entries(data, selected_action_id, ordered_ids)
    if group == "global_parameter":
        global_parameters = data.get("global_parameters")
        return isinstance(global_parameters, dict) and reorder_json_mapping_by_ids(global_parameters, ordered_ids)
    return False


def set_task_action_drag_selection(selection: object, action_id: str) -> None:
    selection.set(selection.get_target(), 8, action_id.encode("utf-8"))


def task_action_drag_selection_id(selection: object) -> str:
    data = selection.get_data()
    if not data:
        return ""
    if isinstance(data, str):
        return data.strip()
    return bytes(data).decode("utf-8").strip()


def parameter_field_order(parameter_type: str, fields: set[str]) -> list[str]:
    preferred_by_type = {
        "board": ["name", "host", "password_file", "tftp_root", "nfs_root", "user", "deployment_folder_name"],
        "file": ["name", "path"],
        "local_file": ["name", "path"],
        "remote_file": ["name", "path"],
    }
    preferred = preferred_by_type.get(parameter_type, ["name"])
    ordered = [field for field in preferred if field in fields]
    ordered.extend(sorted(field for field in fields if field not in set(ordered)))
    return ordered


def parameter_type_fields(data: dict[str, object], parameter_type: str) -> set[str]:
    parameter_types = data.get("parameter_types")
    if not isinstance(parameter_types, dict):
        return set()
    definition = parameter_types.get(parameter_type)
    if not isinstance(definition, dict):
        return set()
    fields = definition.get("fields")
    if not isinstance(fields, dict):
        return set()
    return {field for field in fields if isinstance(field, str)}


def parameter_field_type(data: dict[str, object], parameter_type: str, field_name: str) -> str:
    parameter_types = data.get("parameter_types")
    if not isinstance(parameter_types, dict):
        return "string"
    definition = parameter_types.get(parameter_type)
    if not isinstance(definition, dict):
        return "string"
    fields = definition.get("fields")
    if not isinstance(fields, dict):
        return "string"
    field_schema = fields.get(field_name)
    if isinstance(field_schema, str):
        return field_schema
    if isinstance(field_schema, dict):
        field_type = field_schema.get("type")
        if isinstance(field_type, str) and field_type:
            return field_type
    return "string"


def field_type_enum_values(data: dict[str, object], field_type: str) -> list[str] | None:
    field_types = data.get("field_types")
    if not isinstance(field_types, dict):
        return None
    definition = field_types.get(field_type)
    if not isinstance(definition, dict):
        return None
    if definition.get("type") != "enum":
        return None
    values = definition.get("values")
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        return []
    return values

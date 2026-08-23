from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any
import json


def _load_json(filename: str) -> dict[str, Any]:
    try:
        content = resources.files(__package__).joinpath(filename).read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError):
        content = Path(__file__).with_name(filename).read_text(encoding="utf-8")
    data = json.loads(content)
    if not isinstance(data, dict):
        raise TypeError(f"{filename} must contain a JSON object")
    return data


def _string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise TypeError(f"{key} must be a string")
    return value


def _string_map(data: dict[str, Any], key: str) -> dict[str, str]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise TypeError(f"{key} must be a JSON object")
    result: dict[str, str] = {}
    for map_key, map_value in value.items():
        if not isinstance(map_key, str) or not isinstance(map_value, str):
            raise TypeError(f"{key} must map strings to strings")
        result[map_key] = map_value
    return result


def _entries(data: dict[str, Any], key: str, width: int) -> tuple[tuple[str, ...], ...]:
    value = data.get(key)
    if not isinstance(value, list):
        raise TypeError(f"{key} must be a JSON array")
    entries: list[tuple[str, ...]] = []
    for entry in value:
        if not isinstance(entry, list) or len(entry) != width or not all(isinstance(item, str) for item in entry):
            raise TypeError(f"{key} entries must contain {width} strings")
        entries.append(tuple(entry))
    return tuple(entries)


_STRINGS = _load_json("workspace_catalog.json")
_AGENT_STATUS = _STRINGS.get("agent_status")
if not isinstance(_AGENT_STATUS, dict):
    raise TypeError("agent_status must be a JSON object")
_AGENT_STATUS_MANUAL = _STRINGS.get("agent_status_manual")
if not isinstance(_AGENT_STATUS_MANUAL, dict):
    raise TypeError("agent_status_manual must be a JSON object")

AGENT_STATUS_RUNNING_LABEL = _string(_AGENT_STATUS, "running_label")
AGENT_STATUS_TOOLTIPS = _string_map(_AGENT_STATUS, "tooltips")

AGENT_STATUS_MANUAL_MENU_LABEL = _string(_AGENT_STATUS_MANUAL, "menu_label")
AGENT_STATUS_MANUAL_TITLE = _string(_AGENT_STATUS_MANUAL, "title")
AGENT_STATUS_MANUAL_USAGE_TITLE = _string(_AGENT_STATUS_MANUAL, "usage_title")
AGENT_STATUS_MANUAL_USAGE_ENTRIES = _entries(_AGENT_STATUS_MANUAL, "usage_entries", 2)
AGENT_STATUS_MANUAL_SUBTITLE = _string(_AGENT_STATUS_MANUAL, "subtitle")
AGENT_STATUS_MANUAL_ENTRIES = _entries(_AGENT_STATUS_MANUAL, "entries", 3)

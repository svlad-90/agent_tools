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


TK_STRINGS = _load_json("tk_strings.json")
AI_AGENT_BUTTON_LABELS = _string_map(TK_STRINGS, "ai_agent_button_labels")


def tk_string(key: str, **kwargs: object) -> str:
    value = TK_STRINGS.get(key)
    if not isinstance(value, str):
        raise KeyError(key)
    return value.format(**kwargs) if kwargs else value

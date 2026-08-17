from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import TypeAlias
import json


LanguageMap: TypeAlias = dict[str, str]
TranslationMap: TypeAlias = dict[str, LanguageMap]


def _load_json_mapping(filename: str) -> object:
    try:
        content = resources.files(__package__).joinpath(filename).read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError):
        content = Path(__file__).with_name(filename).read_text(encoding="utf-8")
    return json.loads(content)


def _load_translation_map(filename: str) -> TranslationMap:
    data = _load_json_mapping(filename)
    if not isinstance(data, dict):
        raise TypeError(f"{filename} must contain a JSON object")
    result: TranslationMap = {}
    for key, translations in data.items():
        if not isinstance(key, str) or not isinstance(translations, dict):
            raise TypeError(f"{filename} must map string keys to language objects")
        language_map: LanguageMap = {}
        for language, text in translations.items():
            if not isinstance(language, str) or not isinstance(text, str):
                raise TypeError(f"{filename} must map languages to strings")
            language_map[language] = text
        result[key] = language_map
    return result


def _load_language_instructions(filename: str) -> LanguageMap:
    data = _load_json_mapping(filename)
    if not isinstance(data, dict):
        raise TypeError(f"{filename} must contain a JSON object")
    result: LanguageMap = {}
    for language, text in data.items():
        if not isinstance(language, str) or not isinstance(text, str):
            raise TypeError(f"{filename} must map languages to strings")
        result[language] = text
    return result


TRANSLATIONS = _load_translation_map("gtk_translations.json")
UI_STRINGS = _load_translation_map("gtk_ui_strings.json")
CODEX_LANGUAGE_INSTRUCTIONS = _load_language_instructions("gtk_language_instructions.json")


def ui_string(language: str, key: str, **kwargs: object) -> str:
    translations = UI_STRINGS.get(key)
    if translations is None:
        return key.format(**kwargs) if kwargs else key
    text = translations.get(language) or translations.get("en") or key
    return text.format(**kwargs) if kwargs else text

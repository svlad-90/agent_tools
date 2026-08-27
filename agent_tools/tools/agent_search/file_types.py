from __future__ import annotations

from .common import normalize_extension
from .models import AgentSearchError


FILE_TYPES: dict[str, tuple[str, ...]] = {
    "c": (".c", ".h"),
    "cpp": (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".h"),
    "json": (".json",),
    "md": (".md", ".markdown"),
    "py": (".py",),
    "sh": (".sh", ".bash"),
    "text": (".txt", ".log"),
    "toml": (".toml",),
    "yaml": (".yaml", ".yml"),
}


def expand_extensions(extensions: list[str], type_names: list[str]) -> list[str]:
    result = [normalize_extension(extension) for extension in extensions]
    for type_name in type_names:
        key = type_name.lower()
        if key not in FILE_TYPES:
            known = ", ".join(sorted(FILE_TYPES))
            raise AgentSearchError(f"unknown file type {type_name!r}; known types: {known}")
        result.extend(FILE_TYPES[key])
    return sorted(set(result))

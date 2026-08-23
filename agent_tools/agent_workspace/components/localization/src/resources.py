from __future__ import annotations

from importlib import resources
from pathlib import Path


def catalog_text(filename: str) -> str:
    try:
        return resources.files(__package__).joinpath(filename).read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError):
        return Path(__file__).with_name(filename).read_text(encoding="utf-8")

"""Task context repository registry helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Any

from agent_tools.tools.task_context import load_slots


REPO_REGISTRY_SLOT_CATEGORY = "repo-registry"


@dataclass(frozen=True)
class RepoRegistryValidation:
    repositories: tuple[Path, ...]
    errors: tuple[str, ...]


def repo_registry_paths(task_dir: Path, *, workspace: Path) -> list[Path]:
    slots = load_slots(task_dir, (REPO_REGISTRY_SLOT_CATEGORY,))
    if not slots or not slots[0].content.strip():
        return []
    entries = repo_registry_entries(slots[0].content)
    paths: list[Path] = []
    seen: set[Path] = set()
    for entry in entries:
        repo_path = Path(entry).expanduser()
        if not repo_path.is_absolute():
            repo_path = workspace / repo_path
        repo_path = repo_path.resolve()
        if repo_path in seen:
            continue
        seen.add(repo_path)
        paths.append(repo_path)
    return paths


def validate_repo_registry(task_dir: Path, *, workspace: Path) -> RepoRegistryValidation:
    try:
        paths = repo_registry_paths(task_dir, workspace=workspace)
    except ValueError as error:
        return RepoRegistryValidation((), (str(error),))

    errors: list[str] = []
    valid_paths: list[Path] = []
    for path in paths:
        root, error = _git_repo_root(path)
        if error:
            errors.append(f"{path}: {error}")
            continue
        if root != path:
            errors.append(f"{path}: path is inside git repo {root}, but is not the repo root")
            continue
        valid_paths.append(path)
    return RepoRegistryValidation(tuple(valid_paths), tuple(errors))


def repo_registry_entries(content: str) -> list[str]:
    import yaml

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as error:
        raise ValueError(f"repo-registry slot must be valid YAML or JSON: {error}") from error
    repositories = data.get("repositories") if isinstance(data, dict) else data
    if repositories is None:
        return []
    if not isinstance(repositories, list):
        raise ValueError("repo-registry repositories must be a list")
    paths: list[str] = []
    for index, entry in enumerate(repositories, start=1):
        path = _repo_registry_entry_path(entry)
        if not path:
            raise ValueError(f"repo-registry entry {index} must define a non-empty path")
        paths.append(path)
    return paths


def _repo_registry_entry_path(entry: Any) -> str:
    if isinstance(entry, str):
        return entry.strip()
    if isinstance(entry, dict):
        path = entry.get("path")
        if isinstance(path, str):
            return path.strip()
    return ""


def _git_repo_root(path: Path) -> tuple[Path | None, str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as error:
        return None, str(error)
    except NotADirectoryError as error:
        return None, str(error)
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() if error.stderr else str(error)
        return None, detail
    return Path(result.stdout.strip()).resolve(), ""

"""Task context repository registry helpers."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import yaml

from agent_tools.tools.task_context import load_slots
from agent_tools.tools.task_context import set_slot


REPO_REGISTRY_SLOT_CATEGORY = "repo-registry"


@dataclass(frozen=True)
class RepoRegistryValidation:
    repositories: tuple[Path, ...]
    errors: tuple[str, ...]


@dataclass(frozen=True)
class RepoRegistryEntry:
    path: str
    role: str = ""

    def as_dict(self) -> dict[str, str]:
        result = {"path": self.path}
        if self.role:
            result["role"] = self.role
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    list_parser = subparsers.add_parser("list", help="List registered repositories.")
    _add_common_args(list_parser)
    list_parser.add_argument("--json", action="store_true", help="Render JSON.")
    list_parser.set_defaults(func=_main_list)

    validate_parser = subparsers.add_parser("validate", help="Validate registered repositories.")
    _add_common_args(validate_parser)
    validate_parser.add_argument("--json", action="store_true", help="Render JSON.")
    validate_parser.set_defaults(func=_main_validate)

    add_parser = subparsers.add_parser("add", help="Add a verified repository to repo-registry.")
    _add_common_args(add_parser)
    add_parser.add_argument("--repo", required=True, help="Git repository root to register.")
    add_parser.add_argument("--role", default="", help="Optional repository role.")
    add_parser.add_argument("--json", action="store_true", help="Render JSON.")
    add_parser.set_defaults(func=_main_add)

    remove_parser = subparsers.add_parser("remove", help="Remove a repository from repo-registry.")
    _add_common_args(remove_parser)
    remove_parser.add_argument("--repo", required=True, help="Git repository root to unregister.")
    remove_parser.add_argument("--json", action="store_true", help="Render JSON.")
    remove_parser.set_defaults(func=_main_remove)

    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return int(args.func(args))
    except ValueError as error:
        print(f"repo_registry: error: {error}", file=sys.stderr)
        return 1


def add_repository(
    task_dir: Path,
    *,
    workspace: Path,
    repo: Path,
    role: str = "",
) -> list[RepoRegistryEntry]:
    task_dir = task_dir.resolve()
    workspace = workspace.resolve()
    repo = repo.expanduser().resolve()
    root, error = _git_repo_root(repo)
    if error:
        raise ValueError(f"{repo}: {error}")
    if root != repo:
        raise ValueError(f"{repo}: path is inside git repo {root}, but is not the repo root")

    entries = repo_registry_entry_objects(_repo_registry_content(task_dir))
    new_path = _display_path(repo, workspace)
    role = role.strip()
    updated = False
    result: list[RepoRegistryEntry] = []
    for entry in entries:
        entry_path = _resolved_entry_path(entry.path, workspace)
        if entry_path == repo:
            result.append(RepoRegistryEntry(path=entry.path, role=role or entry.role))
            updated = True
        else:
            result.append(entry)
    if not updated:
        result.append(RepoRegistryEntry(path=new_path, role=role))
    set_slot(task_dir, REPO_REGISTRY_SLOT_CATEGORY, render_repo_registry(result))
    return result


def remove_repository(task_dir: Path, *, workspace: Path, repo: Path) -> list[RepoRegistryEntry]:
    task_dir = task_dir.resolve()
    workspace = workspace.resolve()
    repo = _resolved_entry_path(str(repo.expanduser()), workspace)
    entries = repo_registry_entry_objects(_repo_registry_content(task_dir))
    result: list[RepoRegistryEntry] = []
    removed = False
    for entry in entries:
        if _resolved_entry_path(entry.path, workspace) == repo:
            removed = True
            continue
        result.append(entry)
    if not removed:
        raise ValueError(f"{repo}: repository is not registered")
    set_slot(task_dir, REPO_REGISTRY_SLOT_CATEGORY, render_repo_registry(result))
    return result


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


def repo_registry_entry_objects(content: str) -> list[RepoRegistryEntry]:
    entries = _repo_registry_raw_entries(content)
    result: list[RepoRegistryEntry] = []
    for index, entry in enumerate(entries, start=1):
        path = _repo_registry_entry_path(entry)
        if not path:
            raise ValueError(f"repo-registry entry {index} must define a non-empty path")
        role = entry.get("role", "") if isinstance(entry, dict) else ""
        result.append(RepoRegistryEntry(path=path, role=str(role).strip()))
    return result


def render_repo_registry(entries: list[RepoRegistryEntry]) -> str:
    data = {"repositories": [entry.as_dict() for entry in entries]}
    return yaml.safe_dump(data, sort_keys=False).strip()


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
    return [entry.path for entry in repo_registry_entry_objects(content)]


def _repo_registry_raw_entries(content: str) -> list[object]:
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as error:
        raise ValueError(f"repo-registry slot must be valid YAML or JSON: {error}") from error
    repositories = data.get("repositories") if isinstance(data, dict) else data
    if repositories is None:
        return []
    if not isinstance(repositories, list):
        raise ValueError("repo-registry repositories must be a list")
    return repositories


def _repo_registry_entry_path(entry: Any) -> str:
    if isinstance(entry, str):
        return entry.strip()
    if isinstance(entry, dict):
        path = entry.get("path")
        if isinstance(path, str):
            return path.strip()
    return ""


def _main_list(args: argparse.Namespace) -> int:
    task_dir, workspace = _resolved_common_args(args)
    entries = repo_registry_entry_objects(_repo_registry_content(task_dir))
    if args.json:
        print(json.dumps([entry.as_dict() for entry in entries], indent=2, sort_keys=True))
    else:
        print(render_repo_registry(entries) if entries else "repositories: []")
    return 0


def _main_validate(args: argparse.Namespace) -> int:
    task_dir, workspace = _resolved_common_args(args)
    validation = validate_repo_registry(task_dir, workspace=workspace)
    if args.json:
        print(
            json.dumps(
                {
                    "repositories": [str(path) for path in validation.repositories],
                    "errors": list(validation.errors),
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        for path in validation.repositories:
            print(f"PASS {path}")
        for error in validation.errors:
            print(f"FAIL {error}")
        if not validation.repositories and not validation.errors:
            print("WARN repo-registry is empty")
    return 1 if validation.errors else 0


def _main_add(args: argparse.Namespace) -> int:
    task_dir, workspace = _resolved_common_args(args)
    entries = add_repository(task_dir, workspace=workspace, repo=Path(args.repo), role=args.role)
    if args.json:
        print(json.dumps([entry.as_dict() for entry in entries], indent=2, sort_keys=True))
    else:
        print(render_repo_registry(entries))
    return 0


def _main_remove(args: argparse.Namespace) -> int:
    task_dir, workspace = _resolved_common_args(args)
    entries = remove_repository(task_dir, workspace=workspace, repo=Path(args.repo))
    if args.json:
        print(json.dumps([entry.as_dict() for entry in entries], indent=2, sort_keys=True))
    else:
        print(render_repo_registry(entries) if entries else "repositories: []")
    return 0


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--task", required=True, help="Task directory.")
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace root. Default: current directory.",
    )


def _resolved_common_args(args: argparse.Namespace) -> tuple[Path, Path]:
    workspace = Path(args.workspace).expanduser().resolve()
    task_dir = Path(args.task).expanduser()
    if not task_dir.is_absolute():
        task_dir = workspace / task_dir
    return task_dir.resolve(), workspace


def _repo_registry_content(task_dir: Path) -> str:
    slots = load_slots(task_dir, (REPO_REGISTRY_SLOT_CATEGORY,))
    return slots[0].content if slots else ""


def _display_path(repo: Path, workspace: Path) -> str:
    try:
        return repo.relative_to(workspace).as_posix()
    except ValueError:
        return str(repo)


def _resolved_entry_path(path: str, workspace: Path) -> Path:
    repo_path = Path(path).expanduser()
    if not repo_path.is_absolute():
        repo_path = workspace / repo_path
    return repo_path.resolve()


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

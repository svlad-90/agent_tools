from __future__ import annotations

from pathlib import Path
import subprocess

from agent_tools.tools.repo_registry import add_repository
from agent_tools.tools.repo_registry import main
from agent_tools.tools.repo_registry import remove_repository
from agent_tools.tools.repo_registry import repo_registry_entry_objects
from agent_tools.tools.repo_registry import repo_registry_paths
from agent_tools.tools.repo_registry import validate_repo_registry
from agent_tools.tools.task_context import ensure_database
from agent_tools.tools.task_context import load_slots
from agent_tools.tools.task_context import set_slot


def _init_repo(repo: Path) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_add_repository_records_workspace_relative_repo_root(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task_dir = workspace / "tasks" / "sample-task"
    repo = task_dir / "dev" / "repo"
    repo.mkdir(parents=True)
    _init_repo(repo)
    ensure_database(task_dir)

    entries = add_repository(task_dir, workspace=workspace, repo=repo, role="task-dev")

    assert [entry.as_dict() for entry in entries] == [
        {"path": "tasks/sample-task/dev/repo", "role": "task-dev"}
    ]
    assert repo_registry_paths(task_dir, workspace=workspace) == [repo.resolve()]


def test_add_repository_rejects_path_inside_repo(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task_dir = workspace / "tasks" / "sample-task"
    repo = task_dir / "dev" / "repo"
    nested = repo / "nested"
    nested.mkdir(parents=True)
    _init_repo(repo)
    ensure_database(task_dir)

    try:
        add_repository(task_dir, workspace=workspace, repo=nested)
    except ValueError as error:
        assert "is not the repo root" in str(error)
    else:
        raise AssertionError("nested repo path was accepted")


def test_remove_repository_deletes_existing_entry_without_repo_on_disk(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task_dir = workspace / "tasks" / "sample-task"
    task_dir.mkdir(parents=True)
    ensure_database(task_dir)
    set_slot(
        task_dir,
        "repo-registry",
        "repositories:\n"
        "  - path: tasks/sample-task/dev/repo\n"
        "    role: task-dev\n"
        "  - path: /external/repo\n",
    )

    entries = remove_repository(
        task_dir,
        workspace=workspace,
        repo=workspace / "tasks/sample-task/dev/repo",
    )

    assert [entry.as_dict() for entry in entries] == [{"path": "/external/repo"}]


def test_remove_repository_reports_missing_entry(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task_dir = workspace / "tasks" / "sample-task"
    task_dir.mkdir(parents=True)
    ensure_database(task_dir)

    try:
        remove_repository(task_dir, workspace=workspace, repo=workspace / "repo")
    except ValueError as error:
        assert "repository is not registered" in str(error)
    else:
        raise AssertionError("missing repo removal was accepted")


def test_repo_registry_cli_add_remove_and_validate(tmp_path: Path, capsys) -> None:
    workspace = tmp_path / "workspace"
    task_dir = workspace / "tasks" / "sample-task"
    repo = task_dir / "dev" / "repo"
    repo.mkdir(parents=True)
    _init_repo(repo)
    ensure_database(task_dir)

    add_args = [
        "add",
        "--workspace",
        str(workspace),
        "--task",
        str(task_dir),
        "--repo",
        str(repo),
    ]
    assert main(add_args) == 0
    assert "tasks/sample-task/dev/repo" in capsys.readouterr().out
    assert main(["validate", "--workspace", str(workspace), "--task", str(task_dir)]) == 0
    assert "PASS" in capsys.readouterr().out
    remove_args = [
        "remove",
        "--workspace",
        str(workspace),
        "--task",
        str(task_dir),
        "--repo",
        str(repo),
    ]
    assert main(remove_args) == 0
    assert capsys.readouterr().out.strip() == "repositories: []"

    slots = load_slots(task_dir, ("repo-registry",))
    assert slots[0].content == "repositories: []"


def test_repo_registry_validation_reports_invalid_yaml(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    task_dir.mkdir(parents=True)
    ensure_database(task_dir)
    set_slot(task_dir, "repo-registry", "repositories: broken: yaml:")

    validation = validate_repo_registry(task_dir, workspace=tmp_path)

    assert validation.repositories == ()
    assert "valid YAML" in validation.errors[0]


def test_repo_registry_entry_objects_accepts_string_entries() -> None:
    entries = repo_registry_entry_objects("- /repo\n")

    assert [entry.as_dict() for entry in entries] == [{"path": "/repo"}]

from __future__ import annotations

from pathlib import Path

import yaml


VALIDATION_ROOT = Path(__file__).resolve().parents[1]


def test_validation_policy_files_are_mappings_with_unique_check_ids() -> None:
    paths = [
        VALIDATION_ROOT / "workspace-policy.yaml",
        *sorted((VALIDATION_ROOT / "repos").glob("*.yaml")),
    ]
    assert paths
    for path in paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), path
        check_ids: list[str] = []
        for check in data.get("checks", []):
            assert isinstance(check, dict), path
            assert isinstance(check.get("id"), str) and check["id"], path
            assert check.get("backend") in {
                "builtin",
                "command",
                "paf",
                "task_check",
                "task_command",
            }, path
            assert check.get("cost") in {"cheap", "medium", "heavy"}, path
            check_ids.append(check["id"])
        assert len(check_ids) == len(set(check_ids)), path


def test_repo_policy_files_have_identity_evidence() -> None:
    for path in sorted((VALIDATION_ROOT / "repos").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        repo = data.get("repo")
        assert isinstance(repo, dict), path
        assert isinstance(repo.get("id"), str) and repo["id"], path
        assert repo.get("names") or repo.get("github_repos"), path
        files = repo.get("characteristic_files")
        assert isinstance(files, list) and files, path

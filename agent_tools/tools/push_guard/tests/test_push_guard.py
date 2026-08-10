from __future__ import annotations

import subprocess
from pathlib import Path

from agent_tools.tools.push_guard import _forbidden_pushed_paths
from agent_tools.tools.push_guard import _head_commit


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _init_repo(repo: Path) -> None:
    _git(repo, "init")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.com")


def test_forbidden_pushed_paths_detects_private_environment_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    private_file = repo / "agent_tools" / "paf_workspace" / "domains" / "environments" / "private_envs" / "local.yaml"
    private_file.parent.mkdir(parents=True)
    repo.mkdir(exist_ok=True)
    _init_repo(repo)
    private_file.write_text("secret: true\n", encoding="utf-8")
    _git(repo, "add", str(private_file.relative_to(repo)))
    _git(repo, "commit", "-m", "Add private overlay")

    paths = _forbidden_pushed_paths(repo, [_head_commit(repo, "HEAD")])

    assert paths == ["agent_tools/paf_workspace/domains/environments/private_envs/local.yaml"]

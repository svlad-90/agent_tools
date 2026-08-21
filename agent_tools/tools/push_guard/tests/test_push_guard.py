from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from agent_tools.tools.push_guard import _forbidden_pushed_paths
from agent_tools.tools.push_guard import _guarded_pushed_file_findings
from agent_tools.tools.push_guard import _guarded_staged_file_findings
from agent_tools.tools.push_guard import _head_commit
from agent_tools.tools.push_guard import _print_guarded_findings
from agent_tools.tools.push_guard import _pushed_commits
from agent_tools.tools.push_guard import _task_check_report_for_repo
from agent_tools.tools.push_guard import _validated_receipt_source
from agent_tools.tools.push_guard import check
from agent_tools.tools.push_guard import PushedFileFinding


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


def test_guarded_pushed_file_findings_detects_private_knowledge(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    private_file = repo / "agent_tools" / "knowledge" / "private" / "topics" / "local.md"
    private_file.parent.mkdir(parents=True)
    repo.mkdir(exist_ok=True)
    _init_repo(repo)
    private_file.write_text("- local finding\n", encoding="utf-8")
    _git(repo, "add", str(private_file.relative_to(repo)))
    _git(repo, "commit", "-m", "Add private knowledge")

    findings = _guarded_pushed_file_findings(repo, [_head_commit(repo, "HEAD")])

    assert [(finding.path, finding.reason) for finding in findings] == [
        ("agent_tools/knowledge/private/topics/local.md", "private path must not be pushed")
    ]


def test_guarded_pushed_file_findings_detects_artifacts_and_secrets(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    deb = repo / "agent_tools" / "tool.deb"
    token = repo / "token.txt"
    deb.parent.mkdir(parents=True)
    deb.write_text("not really a package\n", encoding="utf-8")
    fake_token = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
    token.write_text(f"OPENAI_API_KEY={fake_token}\n", encoding="utf-8")
    _git(repo, "add", str(deb.relative_to(repo)), str(token.relative_to(repo)))
    _git(repo, "commit", "-m", "Add guarded files")

    findings = _guarded_pushed_file_findings(repo, [_head_commit(repo, "HEAD")])

    assert ("agent_tools/tool.deb", "artifact-like file suffix '.deb' is blocked") in [
        (finding.path, finding.reason) for finding in findings
    ]
    assert any(finding.path == "token.txt" and "secret pattern" in finding.reason for finding in findings)


def test_pushed_commits_expands_new_branch_range_for_file_guards(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "Initial")

    artifact = repo / "early.zip"
    artifact.write_text("artifact\n", encoding="utf-8")
    _git(repo, "add", "early.zip")
    _git(repo, "commit", "-m", "Add artifact")

    artifact.unlink()
    _git(repo, "rm", "early.zip")
    (repo / "README.md").write_text("base\nclean tip\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "Clean tip")
    head = _head_commit(repo, "HEAD")
    stdin_text = f"refs/heads/topic {head} refs/heads/topic {'0' * 40}\n"

    commits = _pushed_commits(stdin_text, repo)
    findings = _guarded_pushed_file_findings(repo, commits)

    assert len(commits) == 3
    assert ("early.zip", "artifact-like file suffix '.zip' is blocked") in [
        (finding.path, finding.reason) for finding in findings
    ]


def test_guarded_staged_file_findings_detects_artifacts_before_commit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    artifact = repo / "download.zip"
    artifact.write_text("archive bytes\n", encoding="utf-8")
    _git(repo, "add", str(artifact.relative_to(repo)))

    findings = _guarded_staged_file_findings(repo)

    assert [(finding.path, finding.reason) for finding in findings] == [
        ("download.zip", "artifact-like file suffix '.zip' is blocked")
    ]


def test_validated_receipt_source_requires_pass_status_and_matching_commit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    tracked = repo / "tracked.txt"
    tracked.write_text("ok\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "Initial")
    commit = _head_commit(repo, "HEAD")
    receipt = repo / "report" / "validation" / "latest.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(
        json.dumps({"commit": commit, "status": "pass"}) + "\n",
        encoding="utf-8",
    )

    assert _validated_receipt_source(repo, commit, receipt) == "validation receipt: report/validation/latest.json"


def test_guarded_findings_print_validation_command_when_workspace_env_is_set(
    monkeypatch: object,
    capsys: object,
) -> None:
    monkeypatch.setenv("AGENT_TOOLS_WORKSPACE_ROOT", "/workspace/tools")

    _print_guarded_findings([PushedFileFinding("debug-output.deb", "blocked")], action="commit")

    err = capsys.readouterr().err
    assert "PYTHONPATH=/workspace/tools python3 -m agent_tools.tools.validate changed" in err


def test_task_check_report_is_required_for_repositories_inside_tasks(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    workspace = tmp_path / "workspace"
    repo = workspace / "tasks" / "sample-task" / "dev" / "repo"
    repo.mkdir(parents=True)
    task_dir = workspace / "tasks" / "sample-task"
    (task_dir / "TASK_DESCRIPTION.md").write_text("# Task\n", encoding="utf-8")
    monkeypatch.setenv("AGENT_TOOLS_WORKSPACE_ROOT", str(workspace))

    report = _task_check_report_for_repo(repo)

    assert report is not None
    assert "task-context-database-missing" in report


def test_pre_push_check_blocks_repositories_inside_tasks_when_task_check_fails(
    tmp_path: Path,
    monkeypatch: object,
    capsys: object,
) -> None:
    workspace = tmp_path / "workspace"
    repo = workspace / "tasks" / "sample-task" / "dev" / "repo"
    repo.mkdir(parents=True)
    _init_repo(repo)
    (repo / "README.md").write_text("repo\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "Initial")
    task_dir = workspace / "tasks" / "sample-task"
    (task_dir / "TASK_DESCRIPTION.md").write_text("# Task\n", encoding="utf-8")
    monkeypatch.setenv("AGENT_TOOLS_WORKSPACE_ROOT", str(workspace))
    monkeypatch.chdir(repo)
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))

    result = check(SimpleNamespace(allow_override=False))

    assert result == 1
    assert "push blocked by task_check" in capsys.readouterr().err

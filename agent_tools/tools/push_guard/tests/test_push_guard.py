from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agent_tools.tools.push_guard import _forbidden_pushed_paths
from agent_tools.tools.push_guard import _guarded_pushed_file_findings
from agent_tools.tools.push_guard import _guarded_staged_file_findings
from agent_tools.tools.push_guard import _head_commit
from agent_tools.tools.push_guard import _print_guarded_findings
from agent_tools.tools.push_guard import _validated_receipt_source
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

from __future__ import annotations

from pathlib import Path

from paf_workspace.task_check import Check
from paf_workspace.task_check import check_task
from paf_workspace.task_check import initialize_task_layout
from paf_workspace.task_check import render_text


def test_initialize_task_layout_creates_description_and_context(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"

    initialize_checks = initialize_task_layout(task_dir, workspace=tmp_path)
    checks = check_task(task_dir, workspace=tmp_path)

    assert (task_dir / "TASK_DESCRIPTION.md").is_file()
    assert (task_dir / "TASK_CONTEXT.md").is_file()
    assert _has_check(initialize_checks, "PASS", "init-task-description")
    assert _has_check(checks, "PASS", "task-description")


def test_initialize_task_layout_records_task_privacy(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"

    initialize_task_layout(task_dir, workspace=tmp_path, privacy="private")

    assert '"privacy": "private"' in (task_dir / "TASK_METADATA.json").read_text(encoding="utf-8")


def test_nested_worktree_manifests_do_not_make_task_runtime_product(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    nested = task_dir / "dev" / "agent_tools_copy"
    nested.mkdir()
    (nested / ".git").write_text("gitdir: /tmp/worktree\n", encoding="utf-8")
    manifest = nested / "agent_tools" / "paf_workspace" / "templates" / "product-artifacts.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("product:\nartifacts:\ndomains:\nvalidation:\n", encoding="utf-8")

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "PASS", "artifact-manifest-not-required")


def test_task_check_uses_only_task_owned_dev_manifests(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    deep_manifest = task_dir / "dev" / "large-checkout" / "nested" / "product-artifacts.yaml"
    deep_manifest.parent.mkdir(parents=True)
    deep_manifest.write_text("product:\nartifacts:\ndomains:\nvalidation:\n", encoding="utf-8")

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "PASS", "artifact-manifest-not-required")

    shallow_manifest = task_dir / "dev" / "product-artifacts.yaml"
    shallow_manifest.write_text("product:\nartifacts:\ndomains:\nvalidation:\n", encoding="utf-8")

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "PASS", "artifact-manifest")


def test_missing_task_description_is_warning_for_existing_task(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    (task_dir / "TASK_DESCRIPTION.md").unlink()

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "WARN", "task-description-missing")
    assert not any(check.status == "FAIL" for check in checks)


def test_render_text_errors_only_keeps_summary_and_failures(tmp_path: Path) -> None:
    checks = [
        Check("PASS", "layout-dir", "required directory exists"),
        Check("WARN", "task-description-missing", "TASK_DESCRIPTION.md is missing"),
        Check("FAIL", "task-dir", "task directory is missing"),
    ]

    report = render_text(tmp_path / "tasks" / "missing-task", checks, errors_only=True)

    assert "Summary: 1 pass, 1 warn, 1 fail" in report
    assert "FAIL task-dir" in report
    assert "PASS layout-dir" not in report
    assert "WARN task-description-missing" not in report


def _has_check(checks: list[Check], status: str, code: str) -> bool:
    return any(check.status == status and check.code == code for check in checks)

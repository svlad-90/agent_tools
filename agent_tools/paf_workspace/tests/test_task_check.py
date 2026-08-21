from __future__ import annotations

from pathlib import Path

from paf_workspace.task_check import Check
from paf_workspace.task_check import check_task
from paf_workspace.task_check import initialize_task_layout
from paf_workspace.task_check import main
from paf_workspace.task_check import render_text
from agent_tools.tools.task_context import add_entry
from agent_tools.tools.task_context import DATABASE_FILENAME
from agent_tools.tools.task_context import load_entries
from agent_tools.tools.task_context import migrate_legacy_journal


def test_initialize_task_layout_creates_description_and_context(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"

    initialize_checks = initialize_task_layout(task_dir, workspace=tmp_path)
    checks = check_task(task_dir, workspace=tmp_path)

    assert (task_dir / "TASK_DESCRIPTION.md").is_file()
    assert not (task_dir / "TASK_CONTEXT.md").exists()
    assert (task_dir / DATABASE_FILENAME).is_file()
    assert _has_check(initialize_checks, "PASS", "init-task-description")
    assert _has_check(initialize_checks, "PASS", "init-task-context-database")
    assert _has_check(checks, "PASS", "task-description")
    assert _has_check(checks, "PASS", "task-context-database")


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


def test_legacy_task_context_markdown_is_non_strict_warning(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    (task_dir / "TASK_CONTEXT.md").write_text("# Legacy context\n", encoding="utf-8")

    checks = check_task(task_dir, workspace=tmp_path)
    result = main([str(task_dir), "--workspace", str(tmp_path), "--strict-warnings", "--errors-only"])

    assert _has_check(checks, "WARN", "task-context-markdown-legacy")
    assert result == 0


def test_strict_warnings_ignores_auto_runtime_readiness_warnings(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    add_entry(
        task_dir,
        severity="mid",
        summary="Analysis mentions Xen and QEMU",
        details="This is not a runtime validation task yet.",
    )

    result = main([str(task_dir), "--workspace", str(tmp_path), "--strict-warnings", "--errors-only"])

    assert result == 0


def test_strict_warnings_fails_for_scope_metadata_warning(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    (task_dir / "TASK_DESCRIPTION.md").unlink()

    result = main([str(task_dir), "--workspace", str(tmp_path), "--strict-warnings", "--errors-only"])

    assert result == 1


def test_strict_warnings_honors_explicit_runtime_product_flag(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)

    result = main([str(task_dir), "--workspace", str(tmp_path), "--strict-warnings", "--runtime-product", "--errors-only"])

    assert result == 1


def test_missing_task_context_database_is_failure(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    (task_dir / DATABASE_FILENAME).unlink()

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "FAIL", "task-context-database-missing")


def test_invalid_task_context_database_is_failure(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    (task_dir / DATABASE_FILENAME).write_bytes(b"not-a-sqlite-database")

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "FAIL", "task-context-database-invalid")
    assert not _has_check(checks, "PASS", "task-context-active-size")


def test_oversized_active_task_context_is_failure(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    add_entry(
        task_dir,
        severity="high",
        labels=("task-context",),
        summary="Large active journal entry",
        details="word " * 30_000,
    )

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "FAIL", "task-context-active-size")


def test_oversized_resolved_task_context_does_not_fail_active_budget(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    add_entry(
        task_dir,
        severity="high",
        labels=("task-context",),
        status="resolved",
        summary="Large resolved journal entry",
        details="word " * 30_000,
    )

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "PASS", "task-context-active-size")
    assert not _has_check(checks, "FAIL", "task-context-active-size")


def test_legacy_task_context_can_be_migrated(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    (task_dir / DATABASE_FILENAME).unlink()
    (task_dir / "TASK_CONTEXT_LOG.jsonl").write_text(
        '{"timestamp":"2026-08-19T10:00:00","severity":"high","labels":["validation"],'
        '"status":"active","summary":"Legacy entry"}\n',
        encoding="utf-8",
    )

    assert migrate_legacy_journal(task_dir) == 1
    assert not (task_dir / "TASK_CONTEXT_LOG.jsonl").exists()
    assert [entry.summary for entry in load_entries(task_dir)] == ["Legacy entry"]
    assert not (task_dir / "TASK_CONTEXT.md").exists()
    assert _has_check(check_task(task_dir, workspace=tmp_path), "PASS", "task-context-database-valid")


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

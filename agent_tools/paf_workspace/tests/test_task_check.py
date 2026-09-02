from __future__ import annotations

from pathlib import Path

from paf_workspace.task_check import Check
from paf_workspace.task_check import check_task
from paf_workspace.task_check import initialize_task_guard
from paf_workspace.task_check import initialize_task_layout
from paf_workspace.task_check import main
from paf_workspace.task_check import render_text
from agent_tools.tools.task_context import add_entry
from agent_tools.tools.task_context import DATABASE_FILENAME
from agent_tools.tools.task_context import load_entries
from agent_tools.tools.task_context import load_slots
from agent_tools.tools.task_context import migrate_legacy_journal
from agent_tools.tools.task_context import set_slot


def test_initialize_task_layout_creates_context_database_without_description_file(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"

    initialize_checks = initialize_task_layout(task_dir, workspace=tmp_path)
    checks = check_task(task_dir, workspace=tmp_path)

    assert not (task_dir / "TASK_DESCRIPTION.md").exists()
    assert not (task_dir / "TASK_CONTEXT.md").exists()
    assert (task_dir / DATABASE_FILENAME).is_file()
    assert not (task_dir / "front_door_bell.py").exists()
    assert _has_check(initialize_checks, "PASS", "init-task-context-database")
    assert _has_check(initialize_checks, "PASS", "actualize-harness-adapter-ready")
    assert _has_check(checks, "PASS", "task-context-database")
    assert _has_check(checks, "FAIL", "task-context-slot-required")
    assert _has_check(checks, "WARN", "task-guard-missing")


def test_init_layout_command_succeeds_before_context_is_filled(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"

    result = main([str(task_dir), "--workspace", str(tmp_path), "--init-layout"])

    assert result == 0
    assert (task_dir / DATABASE_FILENAME).is_file()
    assert _has_check(check_task(task_dir, workspace=tmp_path), "FAIL", "task-context-slot-required")


def test_initialize_task_layout_records_task_privacy(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"

    initialize_task_layout(task_dir, workspace=tmp_path, privacy="private")

    assert '"privacy": "private"' in (task_dir / "TASK_METADATA.json").read_text(encoding="utf-8")


def test_initialize_task_guard_creates_skeleton_without_overwriting(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"

    checks = initialize_task_guard(task_dir, workspace=tmp_path)
    guard_path = task_dir / "TASK_GUARD.yaml"
    guard_path.write_text("version: 1\nchecks:\n  - id: local\n", encoding="utf-8")
    second_checks = initialize_task_guard(task_dir, workspace=tmp_path)

    assert _has_check(checks, "PASS", "init-task-guard")
    assert guard_path.read_text(encoding="utf-8") == "version: 1\nchecks:\n  - id: local\n"
    assert _has_check(second_checks, "PASS", "init-task-guard-existing")


def test_init_guard_command_succeeds_before_context_is_filled(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"

    result = main([str(task_dir), "--workspace", str(tmp_path), "--init-guard"])

    assert result == 0
    assert (task_dir / "TASK_GUARD.yaml").read_text(encoding="utf-8") == "version: 1\nchecks: []\n"


def test_task_check_validates_task_guard_schema(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    set_slot(task_dir, "goal", "Goal.")
    set_slot(task_dir, "operational-memory", "Current: ready.")
    (task_dir / "TASK_GUARD.yaml").write_text(
        "version: 1\nchecks:\n  - id: bad\n    backend: mystery\n",
        encoding="utf-8",
    )

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "FAIL", "task-guard-invalid")


def test_task_check_accepts_valid_task_guard(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    set_slot(task_dir, "goal", "Goal.")
    set_slot(task_dir, "operational-memory", "Current: ready.")
    (task_dir / "TASK_GUARD.yaml").write_text(
        "version: 1\nchecks:\n  - id: local-smoke\n    backend: command\n    cost: cheap\n",
        encoding="utf-8",
    )

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "PASS", "task-guard")
    assert not _has_check(checks, "WARN", "task-guard-missing")
    assert not _has_check(checks, "FAIL", "task-guard-invalid")


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


def test_required_task_context_slots_are_checked(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "FAIL", "task-context-slot-required")
    set_slot(task_dir, "goal", "Goal.")
    set_slot(task_dir, "operational-memory", "Current: ready.")

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "PASS", "task-context-slot-required")
    assert not _has_check(checks, "FAIL", "task-context-slot-required")


def test_legacy_task_context_markdown_is_non_strict_warning(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    (task_dir / "TASK_CONTEXT.md").write_text("# Legacy context\n", encoding="utf-8")
    set_slot(task_dir, "goal", "Goal.")
    set_slot(task_dir, "operational-memory", "Current: ready.")
    set_slot(task_dir, "env", "Use local env.")
    set_slot(task_dir, "validation", "Run smoke.")

    checks = check_task(task_dir, workspace=tmp_path)
    result = main([str(task_dir), "--workspace", str(tmp_path), "--strict-warnings", "--errors-only"])

    assert _has_check(checks, "WARN", "task-context-markdown-legacy")
    assert result == 1


def test_non_empty_legacy_task_context_slot_is_failure(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    set_slot(task_dir, "goal", "Goal.")
    set_slot(task_dir, "operational-memory", "Current: ready.")
    set_slot(task_dir, "legacy", "Old imported context.")

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "FAIL", "task-context-slot-legacy")
    assert not _has_check(checks, "WARN", "task-context-slot-legacy")


def test_strict_warnings_ignores_auto_runtime_readiness_warnings(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    set_slot(task_dir, "goal", "Goal.")
    set_slot(task_dir, "operational-memory", "Current: ready.")
    set_slot(task_dir, "env", "Use local env.")
    set_slot(task_dir, "validation", "Run smoke.")

    result = main([str(task_dir), "--workspace", str(tmp_path), "--strict-warnings", "--errors-only"])

    assert result == 0


def test_runtime_hints_do_not_require_product_artifact_manifest(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    set_slot(task_dir, "goal", "Inspect QEMU runtime logs.")
    set_slot(task_dir, "operational-memory", "Current: analysis-only task.")
    set_slot(task_dir, "env", "Use local files.")
    set_slot(task_dir, "validation", "Run smoke.")

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "PASS", "artifact-manifest-not-required")
    assert not _has_check(checks, "WARN", "artifact-manifest-missing")


def test_strict_warnings_fails_for_missing_required_slot(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)

    result = main([str(task_dir), "--workspace", str(tmp_path), "--strict-warnings", "--errors-only"])

    assert result == 1


def test_strict_warnings_honors_explicit_runtime_product_flag(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    set_slot(task_dir, "goal", "Goal.")
    set_slot(task_dir, "operational-memory", "Current: ready.")
    set_slot(task_dir, "env", "Use local env.")
    set_slot(task_dir, "validation", "Run smoke.")

    result = main([str(task_dir), "--workspace", str(tmp_path), "--strict-warnings", "--runtime-product", "--errors-only"])

    assert result == 1


def test_missing_task_context_database_is_failure(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    (task_dir / DATABASE_FILENAME).unlink()

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "PASS", "task-context-database")


def test_invalid_task_context_database_is_failure(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    (task_dir / DATABASE_FILENAME).write_bytes(b"not-a-sqlite-database")

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "FAIL", "task-context-database-invalid")
    assert not _has_check(checks, "PASS", "task-context-slots-size")


def test_oversized_task_context_slots_are_failure(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    set_slot(task_dir, "goal", "Goal.")
    set_slot(task_dir, "operational-memory", "word " * 30_000)

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "FAIL", "task-context-slots-size")


def test_normal_task_context_slots_fit_budget(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    set_slot(task_dir, "goal", "Goal.")
    set_slot(task_dir, "operational-memory", "Current: ready.")

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "PASS", "task-context-slots-size")
    assert not _has_check(checks, "FAIL", "task-context-slots-size")


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
        Check("WARN", "task-context-slot-recommended", "recommended context slot is empty: env"),
        Check("FAIL", "task-dir", "task directory is missing"),
    ]

    report = render_text(tmp_path / "tasks" / "missing-task", checks, errors_only=True)

    assert "Summary: 1 pass, 1 warn, 1 fail" in report
    assert "FAIL task-dir" in report
    assert "PASS layout-dir" not in report
    assert "WARN task-context-slot-recommended" not in report


def test_render_text_issues_only_keeps_warnings_and_failures(tmp_path: Path) -> None:
    checks = [
        Check("PASS", "layout-dir", "required directory exists"),
        Check("WARN", "task-context-slot-recommended", "recommended context slot is empty: env"),
        Check("FAIL", "task-dir", "task directory is missing"),
    ]

    report = render_text(tmp_path / "tasks" / "missing-task", checks, issues_only=True)

    assert "Summary: 1 pass, 1 warn, 1 fail" in report
    assert "WARN task-context-slot-recommended" in report
    assert "FAIL task-dir" in report
    assert "PASS layout-dir" not in report


def _has_check(checks: list[Check], status: str, code: str) -> bool:
    return any(check.status == status and check.code == code for check in checks)

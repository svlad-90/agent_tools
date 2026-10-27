from __future__ import annotations

import pytest

from agent_tools.agent_workspace.components.artifacts.src import artifacts as artifacts_module
from agent_tools.agent_workspace.components.test_support.src.helpers import *
from agent_tools.agent_workspace.components.artifacts.api import artifact_path_from_label
from agent_tools.agent_workspace.components.artifacts.api import artifact_text_preview


def test_gtk_task_artifact_entries_groups_task_outputs(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    (task / "report" / "diff").mkdir(parents=True)
    (task / "report" / "puml").mkdir(parents=True)
    (task / "report" / "logs").mkdir(parents=True)
    (task / "report" / "logs" / "runtime.log").write_text("log", encoding="utf-8")
    (task / "report" / "diff" / "review.html").write_text("<html>", encoding="utf-8")
    (task / "report" / "diff" / "review.diff").write_text("diff", encoding="utf-8")
    (task / "report" / "diff" / "comments.json").write_text("{}", encoding="utf-8")
    (task / "report" / "puml" / "flow.svg").write_text("<svg>", encoding="utf-8")
    (task / "report" / "puml" / "flow.puml").write_text("@startuml", encoding="utf-8")
    (task / "report" / "notes.md").write_text("notes", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)

    entries = gtk_task_artifact_entries(summary)

    assert [(entry.group, entry.path.name) for entry in entries] == [
        ("logs", "runtime.log"),
        ("diagrams", "flow.puml"),
        ("diagrams", "flow.svg"),
        ("diff_reports", "comments.json"),
        ("diff_reports", "review.diff"),
        ("diff_reports", "review.html"),
        ("artifacts", "notes.md"),
    ]


def test_gtk_task_artifact_entries_can_sort_by_updated_time(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    (task / "report").mkdir(parents=True)
    older = task / "report" / "a-notes.md"
    newer = task / "report" / "b-notes.md"
    older.write_text("older", encoding="utf-8")
    newer.write_text("newer", encoding="utf-8")
    os.utime(older, (100, 100))
    os.utime(newer, (200, 200))
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)

    assert [entry.path.name for entry in gtk_task_artifact_entries(summary, sort_column="name")] == [
        "a-notes.md",
        "b-notes.md",
    ]
    assert [
        entry.path.name for entry in gtk_task_artifact_entries(summary, sort_column="updated", descending=True)
    ] == [
        "b-notes.md",
        "a-notes.md",
    ]
    assert [
        entry.path.name for entry in gtk_task_artifact_entries(summary, sort_column="updated", descending=False)
    ] == [
        "a-notes.md",
        "b-notes.md",
    ]


def test_gtk_artifact_delete_paths_include_hidden_group_files(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    (task / "report" / "diff").mkdir(parents=True)
    (task / "report" / "puml").mkdir(parents=True)
    files = {
        "report/logs/runtime.log": "log",
        "report/notes.md": "notes",
        "report/diff/review.html": "<html>",
        "report/diff/review.diff": "diff",
        "report/diff/comments.json": "{}",
        "report/puml/flow.svg": "<svg>",
        "report/puml/flow.puml": "@startuml",
    }
    for rel_path, content in files.items():
        path = task / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)

    def rels(paths: list[Path]) -> list[str]:
        return sorted(str(path.relative_to(task)) for path in paths)

    assert gtk_artifact_delete_paths(summary, artifact_path=task / "report" / "logs" / "runtime.log") == [
        task / "report" / "logs" / "runtime.log"
    ]
    assert rels(gtk_artifact_delete_paths(summary, group="logs")) == ["report/logs/runtime.log"]
    assert rels(gtk_artifact_delete_paths(summary, group="diagrams")) == [
        "report/puml/flow.puml",
        "report/puml/flow.svg",
    ]
    assert rels(gtk_artifact_delete_paths(summary, group="diff_reports")) == [
        "report/diff/comments.json",
        "report/diff/review.diff",
        "report/diff/review.html",
    ]
    assert rels(gtk_artifact_delete_paths(summary, group="artifacts")) == ["report/notes.md"]
    assert rels(gtk_artifact_delete_paths(summary, delete_all=True)) == sorted(files)


def test_gtk_artifact_context_action_matches_clicked_area(tmp_path: Path) -> None:
    artifact = tmp_path / "tasks" / "sample-task" / "report" / "runtime.log"

    assert gtk_artifact_context_action(artifact, "logs") == "artifact"
    assert gtk_artifact_context_action(None, "logs") == "group"
    assert gtk_artifact_context_action(None, None) == "all"


def test_gtk_artifact_selectable_path_stays_inside_task(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    artifact_dir = task / "report" / "diff"
    artifact_dir.mkdir(parents=True)
    artifact_path = artifact_dir / "review.html"
    artifact_path.write_text("<html>", encoding="utf-8")
    outside = tmp_path / "outside.html"
    outside.write_text("outside", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)

    assert gtk_artifact_selectable_path(summary, artifact_path) == artifact_path
    assert gtk_artifact_selectable_path(summary, artifact_dir) is None
    assert gtk_artifact_selectable_path(summary, outside) is None


def test_gtk_artifact_updated_label_formats_timestamp() -> None:
    assert gtk_artifact_updated_label(0) == ""
    assert gtk_artifact_updated_label(100) == datetime.fromtimestamp(100).strftime("%Y-%m-%d %H:%M")


def test_artifact_text_preview_reads_bounded_report_text(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    artifact = task / "report" / "notes.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("artifact notes", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)

    preview = artifact_text_preview(summary, "report/notes.md", max_bytes=8)

    assert preview["label"] == "report/notes.md"
    assert preview["content"] == "artifact"
    assert preview["size"] == len("artifact notes")
    assert preview["binary"] is False
    assert preview["truncated"] is True


def test_artifact_path_from_label_rejects_non_report_and_escape_paths(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    report = task / "report"
    report.mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    (report / "outside-link.txt").symlink_to(outside)
    dev_file = task / "dev" / "notes.md"
    dev_file.parent.mkdir()
    dev_file.write_text("dev", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)

    assert artifact_path_from_label(summary, "../outside.txt") is None
    assert artifact_path_from_label(summary, "report/outside-link.txt") is None
    assert artifact_path_from_label(summary, "dev/notes.md") is None


def test_artifact_text_preview_marks_binary_content(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    artifact = task / "report" / "capture.bin"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"\x00\xffbinary")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)

    preview = artifact_text_preview(summary, "report/capture.bin")

    assert preview["content"] == ""
    assert preview["binary"] is True
    with pytest.raises(ValueError, match="max_bytes"):
        artifact_text_preview(summary, "report/capture.bin", max_bytes=0)


def test_artifact_text_preview_keeps_complete_utf8_before_truncated_character(
    tmp_path: Path,
) -> None:
    task = tmp_path / "tasks" / "sample-task"
    artifact = task / "report" / "capture.data"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes("A€B".encode("utf-8"))
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)

    preview = artifact_text_preview(summary, "report/capture.data", max_bytes=2)

    assert preview["content"] == "A"
    assert preview["binary"] is False
    assert preview["truncated"] is True


@pytest.mark.skipif(os.name == "nt", reason="uses POSIX no-follow open")
def test_artifact_text_preview_rejects_directory_swap_after_path_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = tmp_path / "tasks" / "sample-task"
    report = task / "report"
    report.mkdir(parents=True)
    (report / "notes.txt").write_text("inside", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "notes.txt").write_text("outside", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)
    real_resolver = artifacts_module.artifact_path_from_label

    def resolve_then_swap(task_summary: TaskSummary, label: str) -> Path | None:
        resolved = real_resolver(task_summary, label)
        report.rename(task / "report-original")
        report.symlink_to(outside, target_is_directory=True)
        return resolved

    monkeypatch.setattr(artifacts_module, "artifact_path_from_label", resolve_then_swap)

    with pytest.raises(ValueError, match="changed while opening"):
        artifact_text_preview(summary, "report/notes.txt")


def test_windows_final_path_normalization_preserves_unc_root() -> None:
    assert (
        artifacts_module._normalize_windows_final_path(
            "\\\\?\\UNC\\server\\share\\tasks\\sample\\report\\notes.txt"
        )
        == "\\\\server\\share\\tasks\\sample\\report\\notes.txt"
    )
    assert artifacts_module._normalize_windows_final_path("\\\\?\\C:\\tasks\\report") == (
        "C:\\tasks\\report"
    )

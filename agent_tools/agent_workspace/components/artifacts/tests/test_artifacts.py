from __future__ import annotations

from agent_tools.agent_workspace.components.test_support.src.helpers import *


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
        (task / rel_path).write_text(content, encoding="utf-8")
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

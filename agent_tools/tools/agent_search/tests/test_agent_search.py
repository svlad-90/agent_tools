from __future__ import annotations

import json
from pathlib import Path
import subprocess

from agent_tools.tools.agent_search import main
from agent_tools.tools.agent_search.core import file_search
from agent_tools.tools.agent_search.core import render_text_search
from agent_tools.tools.agent_search.core import text_search


def test_text_summary_groups_matches_by_file_and_dir(tmp_path: Path, capsys: object) -> None:
    source = tmp_path / "pkg" / "source.py"
    source.parent.mkdir()
    source.write_text("def target():\n    return 'needle'\n", encoding="utf-8")

    exit_code = main(["text", "needle", str(tmp_path), "--mode", "summary"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "matches=1" in output
    assert "pkg/source.py:2:13" in output


def test_text_ranges_include_context_and_merge_overlaps(tmp_path: Path, capsys: object) -> None:
    source = tmp_path / "source.txt"
    source.write_text("\n".join(f"line {idx}" for idx in range(1, 11)) + "\n", encoding="utf-8")

    exit_code = main(["text", "line [45]", str(tmp_path), "--mode", "ranges", "--around", "1"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "source.txt:3:6 matches=4,5" in output
    assert ">     4  line 4" in output
    assert ">     5  line 5" in output


def test_text_aggregate_uses_duplicate_dlt_group_names(tmp_path: Path, capsys: object) -> None:
    source = tmp_path / "log.txt"
    source.write_text("alpha beta\nalpha gamma\n", encoding="utf-8")

    exit_code = main(["text", r"(?P<GV>\w+) (?P<GV>\w+)", str(tmp_path), "--mode", "aggregate"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "GV=alpha matches=2" in output
    assert "GV=beta matches=1" in output
    assert "GV=gamma matches=1" in output


def test_text_aggregate_uses_ordered_group_names(tmp_path: Path, capsys: object) -> None:
    source = tmp_path / "paths.txt"
    source.write_text("component/src/file.py\ncomponent/tests/test_file.py\n", encoding="utf-8")

    exit_code = main(
            [
                "text",
                r"(?P<as_10_component>component)/(?P<as_20_layer>src|tests)",
                str(tmp_path),
                "--mode",
                "aggregate",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "component=component matches=2" in output
    assert "  layer=src matches=1" in output
    assert "  layer=tests matches=1" in output


def test_file_search_finds_paths_and_extensions(tmp_path: Path, capsys: object) -> None:
    (tmp_path / "gtk_ui.py").write_text("", encoding="utf-8")
    (tmp_path / "gtk_ui.md").write_text("", encoding="utf-8")

    exit_code = main(["files", "gtk", str(tmp_path), "--ext", "py"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "gtk_ui.py" in output
    assert "gtk_ui.md" not in output


def test_file_search_scope_name_ignores_directory_match(tmp_path: Path, capsys: object) -> None:
    directory = tmp_path / "gtk"
    directory.mkdir()
    (directory / "plain.py").write_text("", encoding="utf-8")
    (tmp_path / "gtk_ui.py").write_text("", encoding="utf-8")

    exit_code = main(["files", "gtk", str(tmp_path), "--scope", "name"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "gtk_ui.py" in output
    assert "plain.py" not in output


def test_text_search_type_shortcut_filters_extensions(tmp_path: Path, capsys: object) -> None:
    (tmp_path / "source.py").write_text("needle\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("needle\n", encoding="utf-8")

    exit_code = main(["text", "needle", str(tmp_path), "--type", "py"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "source.py" in output
    assert "notes.md" not in output


def test_show_prints_file_range(tmp_path: Path, capsys: object) -> None:
    source = tmp_path / "source.txt"
    source.write_text("\n".join(f"line {idx}" for idx in range(1, 8)) + "\n", encoding="utf-8")

    exit_code = main(["show", str(source), "--line", "4", "--around", "1"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "source.txt:3:5" in output
    assert "    3  line 3" in output
    assert "    5  line 5" in output


def test_examples_command_lists_known_types(capsys: object) -> None:
    exit_code = main(["examples"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "agent_search examples:" in output
    assert "known --type values:" in output


def test_json_output_is_machine_readable(tmp_path: Path, capsys: object) -> None:
    source = tmp_path / "source.py"
    source.write_text("needle\n", encoding="utf-8")

    exit_code = main(["text", "needle", str(tmp_path), "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["matches"][0]["path"] == "source.py"


def test_json_output_is_bounded(tmp_path: Path, capsys: object) -> None:
    for idx in range(5):
        (tmp_path / f"source_{idx}.py").write_text("needle\n", encoding="utf-8")

    exit_code = main(["text", "needle", str(tmp_path), "--json", "--max-matches-scanned", "2"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_matches"] == 2
    assert len(payload["matches"]) == 2
    assert payload["truncated"] is True


def test_threads_argument_does_not_change_text_result(tmp_path: Path) -> None:
    for idx in range(20):
        (tmp_path / f"file_{idx}.txt").write_text(f"needle {idx}\n", encoding="utf-8")

    one_thread = text_search(root=tmp_path, query="needle", threads=1)
    many_threads = text_search(root=tmp_path, query="needle", threads=4)

    assert [(m.path.name, m.line, m.text) for m in one_thread.matches] == [
        (m.path.name, m.line, m.text) for m in many_threads.matches
    ]


def test_default_threads_path_uses_cpu_based_worker_count(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("needle\n", encoding="utf-8")

    report = text_search(root=tmp_path, query="needle")

    assert len(report.matches) == 1


def test_text_search_prunes_hidden_and_default_ignored_directories(tmp_path: Path) -> None:
    visible = tmp_path / "visible.txt"
    git_file = tmp_path / ".git" / "objects" / "packed"
    hidden_file = tmp_path / ".hidden" / "source.txt"
    visible.write_text("needle\n", encoding="utf-8")
    git_file.parent.mkdir(parents=True)
    hidden_file.parent.mkdir(parents=True)
    git_file.write_text("needle\n", encoding="utf-8")
    hidden_file.write_text("needle\n", encoding="utf-8")

    report = text_search(root=tmp_path, query="needle")

    assert [match.path.name for match in report.matches] == ["visible.txt"]


def test_text_search_respects_gitignore_by_default(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (tmp_path / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    (tmp_path / "kept.txt").write_text("needle\n", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("needle\n", encoding="utf-8")

    report = text_search(root=tmp_path, query="needle")

    assert [match.path.name for match in report.matches] == ["kept.txt"]


def test_text_search_can_disable_gitignore(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (tmp_path / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    (tmp_path / "kept.txt").write_text("needle\n", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("needle\n", encoding="utf-8")

    report = text_search(root=tmp_path, query="needle", use_gitignore=False)

    assert [match.path.name for match in report.matches] == ["ignored.txt", "kept.txt"]


def test_text_search_skips_oversized_and_binary_files(tmp_path: Path) -> None:
    small = tmp_path / "small.txt"
    large = tmp_path / "large.txt"
    binary = tmp_path / "binary.bin"
    small.write_text("needle\n", encoding="utf-8")
    large.write_text("needle and too much data\n", encoding="utf-8")
    binary.write_bytes(b"needle\0data")

    report = text_search(root=tmp_path, query="needle", max_file_bytes=10)

    assert [match.path.name for match in report.matches] == ["small.txt"]
    assert report.files_skipped == 2


def test_render_caps_output_budget(tmp_path: Path) -> None:
    for idx in range(50):
        (tmp_path / f"file_{idx}.txt").write_text("needle " * 20 + "\n", encoding="utf-8")
    report = text_search(root=tmp_path, query="needle", threads=2)

    output = render_text_search(
        report,
        mode="summary",
        options={
            "max_tokens": 80,
            "max_output_lines": 20,
            "max_dirs": 5,
            "max_files": 5,
            "samples": 20,
        },
    )

    assert "truncated: output budget reached" in output


def test_file_search_threaded_result_is_stable(tmp_path: Path) -> None:
    for idx in range(20):
        (tmp_path / f"needle_{idx}.txt").write_text("", encoding="utf-8")

    one_thread = file_search(root=tmp_path, query="needle", threads=1)
    many_threads = file_search(root=tmp_path, query="needle", threads=4)

    assert [m.path.name for m in one_thread.matches] == [m.path.name for m in many_threads.matches]

from __future__ import annotations

import json
from pathlib import Path

from agent_tools.tools.code_map import main


def test_parse_check_accepts_multiple_files(tmp_path: Path, capsys: object) -> None:
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("value = 1\n", encoding="utf-8")
    second.write_text("def run():\n    return 2\n", encoding="utf-8")

    exit_code = main(["parse-check", str(first), str(second)])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert f"{first} :: parse-check ok" in output
    assert f"{second} :: parse-check ok" in output


def test_parse_check_returns_failure_when_any_file_fails(tmp_path: Path, capsys: object) -> None:
    valid = tmp_path / "valid.py"
    invalid = tmp_path / "invalid.py"
    valid.write_text("value = 1\n", encoding="utf-8")
    invalid.write_text("def broken(:\n", encoding="utf-8")

    exit_code = main(["parse-check", str(valid), str(invalid)])

    assert exit_code == 1
    output = capsys.readouterr().out
    assert f"{valid} :: parse-check ok" in output
    assert f"{invalid} :: parse-check error" in output


def test_parse_check_json_wraps_multiple_results(tmp_path: Path, capsys: object) -> None:
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("value = 1\n", encoding="utf-8")
    second.write_text("def broken(:\n", encoding="utf-8")

    exit_code = main(["parse-check", str(first), str(second), "--json"])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert [entry["file_path"] for entry in payload["results"]] == [str(first), str(second)]
    assert [entry["ok"] for entry in payload["results"]] == [True, False]


def test_parse_check_json_keeps_single_file_shape(tmp_path: Path, capsys: object) -> None:
    source = tmp_path / "source.py"
    source.write_text("value = 1\n", encoding="utf-8")

    exit_code = main(["parse-check", str(source), "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["file_path"] == str(source)
    assert payload["ok"] is True
    assert "results" not in payload


def test_map_accepts_multiple_files(tmp_path: Path, capsys: object) -> None:
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("def first():\n    return 1\n", encoding="utf-8")
    second.write_text("class Second:\n    pass\n", encoding="utf-8")

    exit_code = main(["map", str(first), str(second)])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert str(first) in output
    assert "function first" in output
    assert str(second) in output
    assert "class Second" in output


def test_map_json_wraps_multiple_files(tmp_path: Path, capsys: object) -> None:
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("def first():\n    return 1\n", encoding="utf-8")
    second.write_text("class Second:\n    pass\n", encoding="utf-8")

    exit_code = main(["map", str(first), str(second), "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert [entry["file_path"] for entry in payload["maps"]] == [str(first), str(second)]


def test_symbol_get_accepts_multiple_files(tmp_path: Path, capsys: object) -> None:
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("def target():\n    return 1\n", encoding="utf-8")
    second.write_text("def target():\n    return 2\n", encoding="utf-8")

    exit_code = main(["symbol-get", str(first), str(second), "--symbol", "target"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert output.count("symbol: target") == 2
    assert str(first) in output
    assert str(second) in output


def test_symbol_get_json_wraps_multiple_files(tmp_path: Path, capsys: object) -> None:
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("def target():\n    return 1\n", encoding="utf-8")
    second.write_text("def target():\n    return 2\n", encoding="utf-8")

    exit_code = main(["symbol-get", str(first), str(second), "--symbol", "target", "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert [entry["file_path"] for entry in payload["symbols"]] == [str(first), str(second)]
    assert [entry["name"] for entry in payload["symbols"]] == ["target", "target"]


def test_imports_add_accepts_multiple_files_check_only(tmp_path: Path, capsys: object) -> None:
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("value = 1\n", encoding="utf-8")
    second.write_text("value = 2\n", encoding="utf-8")

    exit_code = main(
        [
            "imports-add",
            str(first),
            str(second),
            "--import",
            "import json",
            "--check-only",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert str(first) in output
    assert str(second) in output
    assert first.read_text(encoding="utf-8") == "value = 1\n"
    assert second.read_text(encoding="utf-8") == "value = 2\n"


def test_imports_add_json_wraps_multiple_files(tmp_path: Path, capsys: object) -> None:
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("value = 1\n", encoding="utf-8")
    second.write_text("value = 2\n", encoding="utf-8")

    exit_code = main(["imports-add", str(first), str(second), "--import", "import json", "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["changed"] is True
    assert [entry["file_path"] for entry in payload["results"]] == [str(first), str(second)]
    assert first.read_text(encoding="utf-8").startswith("import json\n")
    assert second.read_text(encoding="utf-8").startswith("import json\n")


def test_replace_symbol_body_reports_unchanged_for_identical_body(
    tmp_path: Path, capsys: object
) -> None:
    source = tmp_path / "source.py"
    source.write_text("def target():\n    return 1\n", encoding="utf-8")
    assert main(["symbol-get", str(source), "--symbol", "target", "--json"]) == 0
    symbol = json.loads(capsys.readouterr().out)

    exit_code = main(
        [
            "replace-symbol-body",
            str(source),
            "--symbol",
            "target",
            "--expect-hash",
            symbol["body_hash"],
            "--replacement-text",
            "    return 1\n",
            "--check-only",
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["changed"] is False
    assert "diff" not in payload
    assert source.read_text(encoding="utf-8") == "def target():\n    return 1\n"


def test_insert_before_symbol_keeps_top_level_separator(tmp_path: Path, capsys: object) -> None:
    source = tmp_path / "source.py"
    source.write_text("import json\n\ndef target():\n    return 1\n", encoding="utf-8")
    assert main(["symbol-get", str(source), "--symbol", "target", "--json"]) == 0
    symbol = json.loads(capsys.readouterr().out)

    exit_code = main(
        [
            "insert-before-symbol",
            str(source),
            "--symbol",
            "target",
            "--expect-hash",
            symbol["node_hash"],
            "--snippet-text",
            "def helper():\n    return 0\n",
        ]
    )

    assert exit_code == 0
    assert source.read_text(encoding="utf-8") == (
        "import json\n\n"
        "def helper():\n"
        "    return 0\n\n"
        "def target():\n"
        "    return 1\n"
    )


def test_insert_after_symbol_keeps_top_level_separator(tmp_path: Path, capsys: object) -> None:
    source = tmp_path / "source.py"
    source.write_text("def target():\n    return 1\n\nvalue = 2\n", encoding="utf-8")
    assert main(["symbol-get", str(source), "--symbol", "target", "--json"]) == 0
    symbol = json.loads(capsys.readouterr().out)

    exit_code = main(
        [
            "insert-after-symbol",
            str(source),
            "--symbol",
            "target",
            "--expect-hash",
            symbol["node_hash"],
            "--snippet-text",
            "def helper():\n    return 0\n",
        ]
    )

    assert exit_code == 0
    assert source.read_text(encoding="utf-8") == (
        "def target():\n"
        "    return 1\n\n"
        "def helper():\n"
        "    return 0\n\n"
        "value = 2\n"
    )

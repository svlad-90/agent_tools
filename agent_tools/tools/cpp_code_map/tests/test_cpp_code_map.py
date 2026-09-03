from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from agent_tools.tools.cpp_code_map.core import (
    CppCodeMapError,
    _read_source,
    _remap_compile_path,
    apply_batch_edits,
    build_compile_doctor,
    render_code_map,
    render_symbol_snapshot,
    render_symbol_index,
    replace_symbol_body,
)


class CppCodeMapTests(unittest.TestCase):
    def test_replace_symbol_body_unwraps_enclosing_braces(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample_project(Path(temp_dir))
            snapshot = json.loads(
                render_symbol_snapshot(source, "add", source.parent, json_output=True)
            )

            result = replace_symbol_body(
                source,
                "add",
                snapshot["body_hash"],
                "\n{\n    return left - right;\n}\n",
                source.parent,
                check_only=True,
            )

        self.assertTrue(result.changed)
        self.assertNotIn("{{", result.diff or "")
        self.assertIn("    return left - right;", result.diff or "")

    def test_replace_symbol_body_accepts_body_only_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample_project(Path(temp_dir))
            snapshot = json.loads(
                render_symbol_snapshot(source, "add", source.parent, json_output=True)
            )

            result = replace_symbol_body(
                source,
                "add",
                snapshot["body_hash"],
                "    return left - right;\n",
                source.parent,
                check_only=True,
            )

        self.assertTrue(result.changed)
        self.assertIn("+    return left - right;", result.diff or "")
        self.assertIn(" {\n", result.diff or "")
        self.assertIn("\n }", result.diff or "")
        self.assertNotIn("{    return", result.diff or "")

    def test_batch_replace_symbol_body_unwraps_enclosing_braces(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample_project(Path(temp_dir))
            snapshot = json.loads(
                render_symbol_snapshot(source, "add", source.parent, json_output=True)
            )

            result = apply_batch_edits(
                [
                    {
                        "command": "replace-symbol-body",
                        "file_path": str(source),
                        "symbol": "add",
                        "expect_hash": snapshot["body_hash"],
                        "replacement_text": "\n{\n    return left - right;\n}\n",
                    }
                ],
                source.parent,
                check_only=True,
            )

        self.assertTrue(result.operations[0].changed)
        self.assertNotIn("{{", result.operations[0].diff or "")
        self.assertIn("    return left - right;", result.operations[0].diff or "")

    def test_missing_source_is_tool_error_not_traceback(self) -> None:
        missing = Path("/tmp/cpp-code-map-missing-source.cpp")

        with self.assertRaises(CppCodeMapError):
            _read_source(missing)

    def test_shallow_compile_db_path_does_not_crash_remap(self) -> None:
        raw_path = Path("/workspace/src/main.cpp")

        remapped = _remap_compile_path(raw_path, Path("/tmp/compile_commands.json"))

        self.assertEqual(raw_path, remapped)

    def test_existing_absolute_compile_db_path_is_not_remapped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.cpp"
            source.write_text("int value;\n", encoding="utf-8")

            remapped = _remap_compile_path(source, Path(temp_dir) / "compile_commands.json")

        self.assertEqual(source, remapped)

    def test_compile_db_entry_missing_is_not_silent_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "missing.cpp"
            source.write_text("int missing() { return 1; }\n", encoding="utf-8")
            other = root / "other.cpp"
            other.write_text("int other() { return 0; }\n", encoding="utf-8")
            _write_compile_db(root, other)

            with self.assertRaises(CppCodeMapError) as raised:
                render_code_map(source, root)

        self.assertIn("compile database entry", raised.exception.message)

    def test_compile_db_entry_missing_can_explicitly_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "missing.cpp"
            source.write_text("int missing() { return 1; }\n", encoding="utf-8")
            other = root / "other.cpp"
            other.write_text("int other() { return 0; }\n", encoding="utf-8")
            _write_compile_db(root, other)

            output = render_code_map(source, root, allow_fallback=True)

        self.assertIn("missing", output)

    def test_compile_doctor_reports_entry_and_args(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample_project(Path(temp_dir))

            result = build_compile_doctor(source, source.parent)

        self.assertTrue(result["ok"])
        self.assertEqual("ok", result["entry"]["status"])
        self.assertEqual("compile_db", result["args"]["source"])

    def test_symbol_index_writes_cache_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = _write_sample_project(root)
            cache_dir = root / ".cache"

            result = json.loads(render_symbol_index((source,),
                                                    source.parent,
                                                    cache_dir=cache_dir,
                                                    json_output=True))

        self.assertTrue(result["ok"])
        self.assertEqual(1, len(result["files"]))
        self.assertGreater(result["files"][0]["symbol_count"], 0)

    def test_workspace_module_entry_point_resolves(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "agent_tools.tools.cpp_code_map", "help"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self.assertEqual("", completed.stderr)
        self.assertEqual(0, completed.returncode)
        self.assertIn("cpp_code_map map", completed.stdout)


def _write_sample_project(root: Path) -> Path:
    source = root / "sample.cpp"
    source.write_text(
        textwrap.dedent(
            """\
            int add(int left, int right)
            {
                return left + right;
            }
            """
        ),
        encoding="utf-8",
    )
    _write_compile_db(root, source)
    return source


def _write_compile_db(root: Path, source: Path) -> None:
    (root / "compile_commands.json").write_text(
        json.dumps([
            {
                "directory": str(root),
                "arguments": [
                    "/usr/bin/c++",
                    "-std=c++17",
                    "-c",
                    str(source),
                    "-o",
                    f"{source.stem}.o",
                ],
                "file": str(source),
            }
        ]),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()

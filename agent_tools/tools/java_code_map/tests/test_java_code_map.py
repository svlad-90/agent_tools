from __future__ import annotations

import json
import os
import shutil
import tempfile
import textwrap
import unittest
from unittest import mock
from pathlib import Path

from agent_tools.tools.java_code_map.core import JavaCompileContext
from agent_tools.tools.java_code_map.core import add_import_statement
from agent_tools.tools.java_code_map.core import apply_batch_edits
from agent_tools.tools.java_code_map.core import render_batch_edit_result
from agent_tools.tools.java_code_map.core import render_code_map
from agent_tools.tools.java_code_map.core import render_compile_doctor
from agent_tools.tools.java_code_map.core import render_edit_result
from agent_tools.tools.java_code_map.core import render_call_graph
from agent_tools.tools.java_code_map.core import render_calls
from agent_tools.tools.java_code_map.core import render_parse_check
from agent_tools.tools.java_code_map.core import render_parse_checks
from agent_tools.tools.java_code_map.core import render_refs
from agent_tools.tools.java_code_map.core import render_symbol_snapshot
from agent_tools.tools.java_code_map.core import replace_symbol_body
from agent_tools.tools.java_code_map import main


class JavaCodeMapTests(unittest.TestCase):
    def test_parse_check_uses_javac_from_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = _write_sample(root)
            _write_fake_javac(root, exit_code=0)

            with mock.patch.dict(os.environ, {"PATH": str(root)}):
                payload = json.loads(render_parse_check(source, JavaCompileContext(), json_output=True))

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["compile_validated"])
        self.assertEqual(str(root / "javac"), payload["command"][0])

    def test_parse_check_reports_javac_diagnostics_from_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = _write_sample(root)
            _write_fake_javac(root, exit_code=1, stderr="Broken.java:1: error: cannot find symbol")

            with mock.patch.dict(os.environ, {"PATH": str(root)}):
                payload = json.loads(render_parse_check(source, JavaCompileContext(), json_output=True))

        self.assertFalse(payload["ok"])
        self.assertFalse(payload["compile_validated"])
        self.assertIn("cannot find symbol", payload["diagnostics"][0])

    def test_cli_parse_check_returns_nonzero_on_javac_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = _write_sample(root)
            _write_fake_javac(root, exit_code=1, stderr="Plugin.java:1: error: cannot find symbol")

            with mock.patch.dict(os.environ, {"PATH": str(root)}):
                result = main(["parse-check", str(source), "--json"])

        self.assertEqual(2, result)

    def test_cli_parse_check_returns_zero_on_javac_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = _write_sample(root)
            _write_fake_javac(root, exit_code=0)

            with mock.patch.dict(os.environ, {"PATH": str(root)}):
                result = main(["parse-check", str(source), "--json"])

        self.assertEqual(0, result)

    def test_map_and_edit_validate_with_javac_from_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = _write_sample(root)
            _write_fake_javac(root, exit_code=0)

            with mock.patch.dict(os.environ, {"PATH": str(root)}):
                mapped = json.loads(render_code_map(source, JavaCompileContext(), json_output=True))
                symbol = json.loads(render_symbol_snapshot(source, "reward", JavaCompileContext(), json_output=True))
                result = replace_symbol_body(
                    source,
                    "reward",
                    symbol["body_hash"],
                    "        return amount + 1;\n",
                    JavaCompileContext(),
                )
                updated_source = source.read_text(encoding="utf-8")

        self.assertTrue(mapped["compile_validated"])
        self.assertIn("sample.Plugin.reward", _flatten_names(mapped["symbols"]))
        self.assertTrue(result.changed)
        self.assertIn("return amount + 1;", updated_source)

    def test_jdt_backend_uses_helper_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = _write_sample(root)
            _write_fake_javac(root, exit_code=0)
            helper = _write_fake_jdt_helper(root, source, stdout_prefix="JVM warning before JSON\n")

            with mock.patch.dict(os.environ, {"PATH": str(root)}):
                payload = json.loads(render_code_map(
                    source,
                    JavaCompileContext(ast_backend="jdt", jdt_helper=helper),
                    json_output=True,
                ))
                symbol = json.loads(render_symbol_snapshot(
                    source,
                    "sample.Plugin.reward",
                    JavaCompileContext(ast_backend="jdt", jdt_helper=helper),
                    json_output=True,
                ))
                result = replace_symbol_body(
                    source,
                    "sample.Plugin.reward",
                    "body-hash",
                    "        return amount + 2;\n",
                    JavaCompileContext(ast_backend="jdt", jdt_helper=helper),
                )
                updated_source = source.read_text(encoding="utf-8")
                calls = json.loads(render_calls(
                    source,
                    JavaCompileContext(ast_backend="jdt", jdt_helper=helper),
                    symbol_name="sample.Plugin.reward",
                    json_output=True,
                ))
                refs = json.loads(render_refs(
                    source,
                    "sample.Plugin.rewards",
                    JavaCompileContext(ast_backend="jdt", jdt_helper=helper),
                    scope_symbol="sample.Plugin.reward",
                    json_output=True,
                ))
                graph = json.loads(render_call_graph(
                    source,
                    JavaCompileContext(ast_backend="jdt", jdt_helper=helper),
                    json_output=True,
                ))

        self.assertEqual("jdt", payload["ast_backend"])
        self.assertTrue(payload["semantic"])
        self.assertEqual("sample.Plugin.reward", symbol["qualified_name"])
        self.assertTrue(result.changed)
        self.assertEqual("body-hash", result.old_hash)
        self.assertIn("return amount + 2;", updated_source)
        self.assertEqual("sample.Plugin.helper", calls["calls"][0]["qualified_name"])
        self.assertEqual("sample.Plugin.rewards", refs["refs"][0]["qualified_name"])
        self.assertEqual("sample.Plugin.reward", graph["edges"][0]["from"])

    def test_jdt_backend_requires_helper_when_forced(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = _write_sample(root)

            with mock.patch.dict(os.environ, {"AGENT_TOOLS_JAVA_CODE_MAP_JDT_HELPER": ""}, clear=False):
                with self.assertRaisesRegex(Exception, "JDT AST helper not found"):
                    render_code_map(
                        source,
                        JavaCompileContext(ast_backend="jdt", jdt_helper=root / "missing-helper"),
                        allow_fallback=True,
                    )

    @unittest.skipUnless(shutil.which("javac"), "javac is required for build-aware Java validation")
    def test_parse_check_uses_javac(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_parse_check(source, JavaCompileContext(), json_output=True))

        self.assertTrue(payload["ok"])
        self.assertIn("javac", payload["command"][0])

    @unittest.skipUnless(shutil.which("javac"), "javac is required for build-aware Java validation")
    def test_parse_check_reports_javac_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "Broken.java"
            source.write_text("public class Broken { public void run() { missing(); } }\n", encoding="utf-8")

            payload = json.loads(render_parse_check(source, JavaCompileContext(), json_output=True))

        self.assertFalse(payload["ok"])
        self.assertTrue(any("cannot find symbol" in diagnostic for diagnostic in payload["diagnostics"]))

    @unittest.skipUnless(shutil.which("javac"), "javac is required for build-aware Java validation")
    def test_multi_file_parse_check_preserves_cpp_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = _write_sample(root)
            second = root / "Helper.java"
            second.write_text("public class Helper { public int value() { return 2; } }\n", encoding="utf-8")

            payload = json.loads(render_parse_checks((first, second), JavaCompileContext(), json_output=True))

        self.assertTrue(payload["ok"])
        self.assertEqual([str(first), str(second)], [item["file"] for item in payload["files"]])

    @unittest.skipUnless(shutil.which("javac"), "javac is required for build-aware Java validation")
    def test_map_and_symbol_get_are_javac_validated_structural(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            mapped = json.loads(render_code_map(source, JavaCompileContext(), json_output=True))
            symbol = json.loads(render_symbol_snapshot(source, "reward", JavaCompileContext(), json_output=True))

        self.assertTrue(mapped["compile_validated"])
        self.assertEqual("javac-validated-structural", mapped["confidence"])
        self.assertIn("sample.Plugin.reward", _flatten_names(mapped["symbols"]))
        self.assertEqual("sample.Plugin.reward", symbol["qualified_name"])
        self.assertIsNotNone(symbol["body_hash"])

    @unittest.skipUnless(shutil.which("javac"), "javac is required for build-aware Java validation")
    def test_replace_symbol_body_revalidates_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))
            snapshot = json.loads(render_symbol_snapshot(source, "reward", JavaCompileContext(), json_output=True))

            result = replace_symbol_body(
                source,
                "reward",
                snapshot["body_hash"],
                "        return amount + 1;\n",
                JavaCompileContext(),
            )

        self.assertTrue(result.changed)
        self.assertIn("return amount + 1;", source.read_text(encoding="utf-8"))

    def test_imports_add_and_batch_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            import_result = add_import_statement(source, "java.util.List", check_only=True)
            batch = apply_batch_edits(
                {
                    "operations": [
                        {
                            "operation": "imports-add",
                            "file_path": str(source),
                            "import": "java.util.Map",
                        }
                    ]
                },
                JavaCompileContext(),
                check_only=True,
            )

            import_payload = json.loads(render_edit_result(import_result, json_output=True))
            batch_payload = json.loads(render_batch_edit_result(batch, json_output=True))
            persisted_source = source.read_text(encoding="utf-8")

        self.assertTrue(import_payload["changed"])
        self.assertTrue(batch_payload["check_only"])
        self.assertEqual("imports-add", batch_payload["operations"][0]["operation"])
        self.assertNotIn("java.util.List", persisted_source)

    @unittest.skipUnless(shutil.which("javac"), "javac is required for build-aware Java validation")
    def test_doctor_reports_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = _write_sample(root)

            payload = json.loads(render_compile_doctor(source, JavaCompileContext(sourcepath=(root,)), json_output=True))

        self.assertTrue(payload["ok"])
        self.assertEqual(str(root), payload["sourcepath"][0]["path"])

    def test_missing_javac_is_reported_without_fallback(self) -> None:
        if shutil.which("javac"):
            self.skipTest("host has javac")
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_parse_check(source, JavaCompileContext(), json_output=True))

        self.assertFalse(payload["ok"])
        self.assertEqual(["javac not found"], payload["diagnostics"])

    def test_allow_fallback_does_not_hide_tree_sitter_syntax_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "Broken.java"
            source.write_text("public class Broken { public void run( { }\n", encoding="utf-8")

            payload = json.loads(render_parse_check(source, JavaCompileContext(), allow_fallback=True, json_output=True))

        self.assertFalse(payload["ok"])
        self.assertFalse(payload["compile_validated"])
        self.assertTrue(any("tree-sitter" in diagnostic for diagnostic in payload["diagnostics"]))


def _write_sample(root: Path) -> Path:
    source = root / "Plugin.java"
    source.write_text(
        textwrap.dedent(
            """
            package sample;

            public class Plugin {
                private int rewards = 0;

                public int reward(int amount) {
                    for (int i = 0; i < amount; i++) {
                        rewards += i;
                    }
                    if (amount > 0) {
                        return rewards;
                    }
                    return 0;
                }
            }
            """
        ).lstrip(),
        encoding="utf-8",
    )
    return source


def _write_fake_javac(root: Path, *, exit_code: int, stderr: str = "") -> Path:
    javac = root / "javac"
    javac.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' '{stderr}' >&2\n"
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    javac.chmod(0o755)
    return javac


def _write_fake_jdt_helper(root: Path, source: Path, *, stdout_prefix: str = "") -> Path:
    helper = root / "jdt-helper"
    text = source.read_text(encoding="utf-8")
    start = text.index("public int reward")
    class_end = text.rindex("}\n")
    end = text.rindex("    }\n", 0, class_end) + len("    }\n")
    body_start = text.index("{", start) + 1
    body_end = end - len("    }\n")
    rewards_offset = text.index("rewards += i")
    helper_offset = text.index("reward")
    payload = {
        "file": str(source),
        "schema_version": 1,
        "engine": "jdt",
        "ast_backend": "jdt",
        "semantic": True,
        "confidence": "jdt-ast",
        "diagnostics": [],
        "symbols": [
            {
                "name": "Plugin",
                "qualified_name": "sample.Plugin",
                "kind": "class",
                "span": {
                    "start_line": 3,
                    "start_column": 1,
                    "end_line": 13,
                    "end_column": 2,
                    "start_offset": text.index("public class Plugin"),
                    "end_offset": len(text),
                },
                "body_span": None,
                "hash": "class-hash",
                "body_hash": None,
                "children": [
                    {
                        "name": "reward",
                        "qualified_name": "sample.Plugin.reward",
                        "kind": "method",
                        "span": {
                            "start_line": 6,
                            "start_column": 5,
                            "end_line": 12,
                            "end_column": 6,
                            "start_offset": start,
                            "end_offset": end,
                        },
                        "body_span": {
                            "start_line": 6,
                            "start_column": 35,
                            "end_line": 12,
                            "end_column": 5,
                            "start_offset": body_start,
                            "end_offset": body_end,
                        },
                        "hash": "method-hash",
                        "body_hash": "body-hash",
                        "children": [],
                    }
                ],
            }
        ],
        "references": [
            {
                "name": "rewards",
                "qualified_name": "sample.Plugin.rewards",
                "binding_key": "Lsample/Plugin;.rewards",
                "binding_kind": "field",
                "kind": "reference",
                "line": 8,
                "column": 13,
                "span": {
                    "start_line": 8,
                    "start_column": 13,
                    "end_line": 8,
                    "end_column": 20,
                    "start_offset": rewards_offset,
                    "end_offset": rewards_offset + len("rewards"),
                },
                "text": "rewards",
                "enclosing_symbol": "sample.Plugin.reward",
            }
        ],
        "calls": [
            {
                "name": "helper",
                "qualified_name": "sample.Plugin.helper",
                "binding_key": "Lsample/Plugin;.helper()I",
                "kind": "method_invocation",
                "line": 8,
                "column": 13,
                "span": {
                    "start_line": 8,
                    "start_column": 13,
                    "end_line": 8,
                    "end_column": 19,
                    "start_offset": helper_offset,
                    "end_offset": helper_offset + len("reward"),
                },
                "text": "helper",
                "enclosing_symbol": "sample.Plugin.reward",
            }
        ],
        "call_graph": [
            {
                "from": "sample.Plugin.reward",
                "to": "sample.Plugin.helper",
                "name": "helper",
                "line": 8,
                "column": 13,
                "binding_key": "Lsample/Plugin;.helper()I",
            }
        ],
    }
    helper.write_text(
        "#!/bin/sh\n"
        f"printf '%s' '{stdout_prefix}'\n"
        "printf '%s\\n' '"
        + json.dumps(payload)
        + "'\n",
        encoding="utf-8",
    )
    helper.chmod(0o755)
    return helper


def _flatten_names(symbols: list[dict[str, object]]) -> set[str]:
    names: set[str] = set()
    for symbol in symbols:
        names.add(str(symbol["qualified_name"]))
        names.update(_flatten_names(symbol.get("children", [])))  # type: ignore[arg-type]
    return names

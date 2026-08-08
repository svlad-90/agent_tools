from __future__ import annotations

import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from codex_tools.tools.cpp_light_code_map.core import render_calls
from codex_tools.tools.cpp_light_code_map.core import render_call_graph
from codex_tools.tools.cpp_light_code_map.core import render_complexity
from codex_tools.tools.cpp_light_code_map.core import render_diagnose
from codex_tools.tools.cpp_light_code_map.core import render_includes
from codex_tools.tools.cpp_light_code_map.core import render_index
from codex_tools.tools.cpp_light_code_map.core import render_index_dir
from codex_tools.tools.cpp_light_code_map.core import render_insert_relative_to_symbol
from codex_tools.tools.cpp_light_code_map.core import render_locals
from codex_tools.tools.cpp_light_code_map.core import render_macros
from codex_tools.tools.cpp_light_code_map.core import render_map
from codex_tools.tools.cpp_light_code_map.core import render_query
from codex_tools.tools.cpp_light_code_map.core import render_refs
from codex_tools.tools.cpp_light_code_map.core import render_rename_symbol
from codex_tools.tools.cpp_light_code_map.core import render_replace_symbol
from codex_tools.tools.cpp_light_code_map.core import render_replace_symbol_body
from codex_tools.tools.cpp_light_code_map.core import render_symbol_snapshot
from codex_tools.tools.cpp_light_code_map.core import render_symbols
from codex_tools.tools.cpp_light_code_map.core import render_unmapped


class CppLightCodeMapTests(unittest.TestCase):
    def test_map_finds_structural_symbols_without_compile_db(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_map(source, json_output=True))

        self.assertEqual("tree-sitter", payload["engine"])
        self.assertEqual(2, payload["schema_version"])
        self.assertFalse(payload["semantic"])
        names = _flatten_names(payload["symbols"])
        self.assertIn("demo::Device", names)
        self.assertIn("demo::Device::start", names)
        self.assertIn("demo::helper", names)

    def test_map_reports_extended_symbol_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_map(source, json_output=True))

        kinds = _flatten_kinds(payload["symbols"])
        self.assertIn("type_alias", kinds)
        self.assertIn("enum_value", kinds)
        self.assertIn("field", kinds)
        self.assertIn("global_variable", kinds)
        self.assertTrue({"method", "constructor", "destructor"} & kinds)

    def test_symbol_get_returns_body_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_symbol_snapshot(source, "demo::helper", json_output=True))

        self.assertEqual("demo::helper", payload["qualified_name"])
        self.assertIsNotNone(payload["body_hash"])

    def test_symbol_get_can_include_preceding_doc_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_symbol_snapshot(source, "demo::helper", with_doc=True, json_output=True))

        self.assertIn("Helper returns", payload["doc"])

    def test_symbols_filters_by_kind_name_and_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))
            helper_line = source.read_text(encoding="utf-8").splitlines().index("int helper(int seed)") + 1

            payload = json.loads(render_symbols(source,
                                                kind="function",
                                                name="helper",
                                                contains_line=helper_line,
                                                json_output=True))

        self.assertEqual(["demo::helper"], [symbol["qualified_name"] for symbol in payload["symbols"]])

    def test_map_supports_compact_outline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            output = render_map(source, compact=True)

        self.assertIn("function demo::helper", output)
        self.assertNotIn("body_hash=", output)

    def test_includes_lists_include_directives(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_includes(source, json_output=True))

        self.assertEqual("#include <stdint.h>", payload["includes"][0]["text"])

    def test_macros_lists_preprocessor_definitions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_macros(source, json_output=True))

        self.assertIn("DEVICE_LIMIT", [macro["name"] for macro in payload["macros"]])

    def test_calls_lists_call_expressions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_calls(source, symbol_name="demo::helper", json_output=True))

        self.assertEqual(["normalize", "bump", "device.start"], [call["name"] for call in payload["calls"]])
        self.assertTrue(all(call["enclosing_symbol"] == "demo::helper" for call in payload["calls"]))

    def test_call_graph_lists_edges(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_call_graph(source, json_output=True))

        self.assertIn(("demo::helper", "normalize"), [(edge["from"], edge["to"]) for edge in payload["edges"]])

    def test_refs_lists_identifier_occurrences(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_refs(source, "Device", json_output=True))

        self.assertGreaterEqual(len(payload["refs"]), 1)
        self.assertTrue(all(ref["kind"] in {"identifier", "field_identifier", "type_identifier", "namespace_identifier"}
                            for ref in payload["refs"]))
        self.assertTrue(all(ref["category"] in {"declaration", "field", "identifier", "type"} for ref in payload["refs"]))

    def test_refs_can_be_scoped_to_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_refs(source, "Device", scope_symbol="demo::helper", json_output=True))

        self.assertEqual(["demo::helper"], sorted({ref["enclosing_symbol"] for ref in payload["refs"]}))

    def test_locals_lists_parameters_locals_and_labels(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_locals(source, "demo::helper", json_output=True))

        names = {(item["kind"], item["name"]) for item in payload["locals"]}
        self.assertIn(("parameter", "seed"), names)
        self.assertIn(("local", "device"), names)
        self.assertIn(("local", "value"), names)
        self.assertIn(("label", "label"), names)

    def test_complexity_counts_structural_control_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_complexity(source, symbol_name="demo::helper", json_output=True))

        metric = payload["metrics"][0]
        self.assertEqual("demo::helper", metric["symbol"])
        self.assertEqual(1, metric["branches"])
        self.assertEqual(1, metric["loops"])
        self.assertEqual(2, metric["returns"])
        self.assertEqual(3, metric["calls"])

    def test_replace_symbol_body_check_only_uses_body_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))
            snapshot = json.loads(render_symbol_snapshot(source, "demo::helper", json_output=True))

            output = render_replace_symbol_body(source,
                                                "demo::helper",
                                                snapshot["body_hash"],
                                                "\n{\n    return 9;\n}\n",
                                                check_only=True)

        self.assertIn("changed=true", output)
        self.assertIn("return 9;", output)

    def test_replace_symbol_check_only_uses_symbol_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))
            snapshot = json.loads(render_symbol_snapshot(source, "demo::normalize", json_output=True))

            output = render_replace_symbol(source,
                                           "demo::normalize",
                                           snapshot["hash"],
                                           "int normalize(int value)\n{\n    return value;\n}\n",
                                           check_only=True)

        self.assertIn("replace-symbol", output)
        self.assertIn("return value;", output)

    def test_rename_symbol_check_only_uses_symbol_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))
            snapshot = json.loads(render_symbol_snapshot(source, "demo::normalize", json_output=True))

            output = render_rename_symbol(source,
                                          "demo::normalize",
                                          snapshot["hash"],
                                          "normalize_value",
                                          check_only=True)

        self.assertIn("rename-symbol", output)
        self.assertIn("normalize_value", output)

    def test_insert_before_and_after_symbol_check_only_use_anchor_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))
            snapshot = json.loads(render_symbol_snapshot(source, "demo::helper", json_output=True))

            before = render_insert_relative_to_symbol(source,
                                                      "demo::helper",
                                                      snapshot["hash"],
                                                      "int before_helper() { return 0; }\n",
                                                      position="before",
                                                      check_only=True)
            after = render_insert_relative_to_symbol(source,
                                                     "demo::helper",
                                                     snapshot["hash"],
                                                     "int after_helper() { return 0; }\n",
                                                     position="after",
                                                     check_only=True)

        self.assertIn("before_helper", before)
        self.assertIn("after_helper", after)

    def test_index_and_query_cached_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = _write_sample(root)
            cache_dir = root / "cache"

            index_payload = json.loads(render_index((source,), cache_dir=cache_dir, json_output=True))
            query_payload = json.loads(render_query("normalize", cache_dir=cache_dir, json_output=True))

        self.assertTrue(index_payload["ok"])
        self.assertEqual(2, index_payload["schema_version"])
        self.assertEqual(["demo::normalize"], [match["symbol"]["qualified_name"] for match in query_payload["matches"]])

    def test_index_dir_indexes_matching_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = _write_sample(root)
            (root / "build").mkdir()
            (root / "build" / "ignored.cpp").write_text("int ignored() { return 0; }\n", encoding="utf-8")
            cache_dir = root / "cache"

            payload = json.loads(render_index_dir(root,
                                                  includes=("*.cpp",),
                                                  cache_dir=cache_dir,
                                                  json_output=True))

        self.assertTrue(payload["ok"])
        self.assertEqual([str(source.resolve())], [item["file"] for item in payload["files"]])

    def test_diagnose_reports_tree_sitter_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_diagnose(source, json_output=True))

        self.assertTrue(payload["ok"])
        self.assertEqual("tree-sitter", payload["engine"])
        self.assertGreater(payload["symbol_count"], 0)
        self.assertIn("tree-sitter", payload["packages"])

    def test_unmapped_reports_coverage_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_unmapped(source, json_output=True))

        self.assertEqual(2, payload["schema_version"])
        self.assertIn("node_types", payload)

    def test_c_struct_pointer_parameter_is_not_struct_definition(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "sample.c"
            source.write_text(
                textwrap.dedent(
                    """\
                    struct device;

                    int open_device(struct device *dev)
                    {
                        return dev != 0;
                    }
                    """
                ),
                encoding="utf-8",
            )

            payload = json.loads(render_map(source, json_output=True))

        self.assertEqual(["open_device"], [symbol["qualified_name"] for symbol in payload["symbols"]])


def _write_sample(root: Path) -> Path:
    source = root / "sample.cpp"
    source.write_text(
        textwrap.dedent(
            """\
            #include <stdint.h>
            #define DEVICE_LIMIT 4

            namespace demo {
            using Count = int;
            enum Mode {
                kFast,
            };
            int global_value = 0;

            struct Device {
                int status;
                Device()
                {
                    status = 0;
                }
                ~Device()
                {
                    status = 0;
                }
                int start()
                {
                    return 1;
                }
            };

            static int normalize(int value)
            {
                if (value > DEVICE_LIMIT) {
                    return DEVICE_LIMIT;
                }
                return value;
            }

            /**
             * Helper returns a normalized start result.
             */
            int helper(int seed)
            {
                Device device;
                auto bump = [](int input) {
                    return input + 1;
                };
            label:
                int value = normalize(seed);
                for (int i = 0; i < 1; ++i) {
                    value += bump(device.start());
                }
                if (value == 0) {
                    goto label;
                }
                return value;
            }
            }
            """
        ),
        encoding="utf-8",
    )
    return source


def _flatten_names(symbols: list[dict[str, object]]) -> set[str]:
    result: set[str] = set()
    for symbol in symbols:
        result.add(str(symbol["qualified_name"]))
        result.update(_flatten_names(symbol["children"]))  # type: ignore[arg-type]
    return result


def _flatten_kinds(symbols: list[dict[str, object]]) -> set[str]:
    result: set[str] = set()
    for symbol in symbols:
        result.add(str(symbol["kind"]))
        result.update(_flatten_kinds(symbol.get("children", [])))  # type: ignore[arg-type]
    return result


if __name__ == "__main__":
    unittest.main()

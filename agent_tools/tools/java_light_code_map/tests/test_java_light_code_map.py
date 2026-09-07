from __future__ import annotations

import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from agent_tools.tools.java_light_code_map.core import render_annotations
from agent_tools.tools.java_light_code_map.core import render_calls
from agent_tools.tools.java_light_code_map.core import render_complexity
from agent_tools.tools.java_light_code_map.core import render_imports
from agent_tools.tools.java_light_code_map.core import render_locals
from agent_tools.tools.java_light_code_map.core import render_map
from agent_tools.tools.java_light_code_map.core import render_parse_check
from agent_tools.tools.java_light_code_map.core import render_refs
from agent_tools.tools.java_light_code_map.core import render_symbol_snapshot


class JavaLightCodeMapTests(unittest.TestCase):
    def test_map_finds_java_symbols_without_build_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_map(source, json_output=True))

        self.assertEqual("tree-sitter", payload["engine"])
        self.assertFalse(payload["semantic"])
        names = _flatten_names(payload["symbols"])
        self.assertIn("dev.agent.SlayerPlugin", names)
        self.assertIn("dev.agent.SlayerPlugin.onEnable", names)
        self.assertIn("dev.agent.SlayerPlugin.reward", names)
        self.assertIn("dev.agent.SlayerPlugin.Mode", names)
        self.assertIn("dev.agent.SlayerPlugin.Mode.FAST", names)

    def test_imports_and_annotations_are_structural(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            imports = json.loads(render_imports(source, json_output=True))
            annotations = json.loads(render_annotations(source, json_output=True))

        self.assertEqual("package dev.agent;", imports["imports"][0]["text"])
        self.assertIn("import org.bukkit.plugin.java.JavaPlugin;", [item["text"] for item in imports["imports"]])
        self.assertIn("Override", [item["name"] for item in annotations["annotations"]])

    def test_symbol_snapshot_returns_body_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_symbol_snapshot(source, "dev.agent.SlayerPlugin.reward", json_output=True))

        self.assertEqual("dev.agent.SlayerPlugin.reward", payload["qualified_name"])
        self.assertEqual("method", payload["kind"])
        self.assertIsNotNone(payload["body_hash"])

    def test_calls_refs_locals_and_complexity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            calls = json.loads(render_calls(source, symbol_name="reward", json_output=True))
            refs = json.loads(render_refs(source, "amount", scope_symbol="reward", json_output=True))
            locals_payload = json.loads(render_locals(source, "reward", json_output=True))
            complexity = json.loads(render_complexity(source, symbol_name="reward", json_output=True))

        self.assertIn("getServer", [call["name"] for call in calls["calls"]])
        self.assertTrue(refs["refs"])
        local_names = {(item["kind"], item["name"]) for item in locals_payload["locals"]}
        self.assertIn(("parameter", "player"), local_names)
        self.assertIn(("parameter", "amount"), local_names)
        self.assertIn(("local", "mode"), local_names)
        metric = complexity["metrics"][0]
        self.assertEqual("dev.agent.SlayerPlugin.reward", metric["symbol"])
        self.assertEqual(1, metric["branches"])
        self.assertEqual(1, metric["loops"])

    def test_parse_check_reports_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = _write_sample(Path(temp_dir))

            payload = json.loads(render_parse_check(source, json_output=True))

        self.assertTrue(payload["ok"])
        self.assertGreaterEqual(payload["symbol_count"], 5)


def _write_sample(root: Path) -> Path:
    source = root / "SlayerPlugin.java"
    source.write_text(
        textwrap.dedent(
            """
            package dev.agent;

            import org.bukkit.entity.Player;
            import org.bukkit.plugin.java.JavaPlugin;

            public class SlayerPlugin extends JavaPlugin {
                private int rewards = 0;

                enum Mode {
                    FAST,
                    SAFE
                }

                @Override
                public void onEnable() {
                    getLogger().info("ready");
                }

                public int reward(Player player, int amount) {
                    Mode mode = Mode.FAST;
                    for (int i = 0; i < amount; i++) {
                        rewards += i;
                    }
                    if (amount > 0) {
                        getServer().broadcastMessage(player.getName());
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


def _flatten_names(symbols: list[dict[str, object]]) -> set[str]:
    names: set[str] = set()
    for symbol in symbols:
        names.add(str(symbol["qualified_name"]))
        names.update(_flatten_names(symbol.get("children", [])))  # type: ignore[arg-type]
    return names

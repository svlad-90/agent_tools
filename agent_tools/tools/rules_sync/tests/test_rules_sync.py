from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_tools.tools.rules_sync.core import (
    RulesSyncError,
    apply_plan,
    discover_rules,
    discover_skills,
    find_project_root,
    plan_all,
    render_claude_always_block,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_workspace(root: Path) -> None:
    _write(root / "AGENTS.md", "# Workspace instructions\n")
    _write(
        root / "CLAUDE.md",
        "# Claude Code workspace instructions\n\nRead and follow `AGENTS.md`.\n",
    )
    _write(
        root / "agent_tools" / "rules" / "always-one.md",
        (
            "---\n"
            "sync: always\n"
            "---\n\n"
            "# Always One\n\n"
            "These rules apply to every task.\n\n"
            "1. Do the thing.\n"
        ),
    )
    _write(
        root / "agent_tools" / "rules" / "skill-covered.md",
        (
            "---\n"
            "sync: skill\n"
            "---\n\n"
            "# Skill Covered\n\n"
            "These rules apply to widget code.\n\n"
            "1. Use the widget tool.\n"
        ),
    )
    _write(
        root / "agent_tools" / "rules" / "skill-orphan.md",
        (
            "---\n"
            "sync: skill\n"
            "---\n\n"
            "# Skill Orphan\n\n"
            "These rules apply to gadget code.\n\n"
            "1. Use the gadget tool.\n"
        ),
    )
    _write(
        root / "agent_tools" / "rules" / "ignored.md",
        (
            "---\n"
            "sync: none\n"
            "---\n\n"
            "# Ignored\n\n"
            "These rules apply to nothing that matters here.\n"
        ),
    )
    _write(
        root / "agent_tools" / "skills" / "widget-tool" / "SKILL.md",
        (
            "---\n"
            "name: widget-tool\n"
            "description: Use when Codex works on widgets.\n"
            "rule: agent_tools/rules/skill-covered.md\n"
            "---\n\n"
            "# Widget Tool\n\n"
            "Codex should run the widget CLI for widget work.\n"
        ),
    )
    _write(
        root / "agent_tools" / "skills" / "standalone-tool" / "SKILL.md",
        (
            "---\n"
            "name: standalone-tool\n"
            "description: Use when Codex needs the standalone tool.\n"
            "---\n\n"
            "# Standalone Tool\n\n"
            "No paired rule file for this one.\n"
        ),
    )


class RulesSyncDiscoveryTests(unittest.TestCase):
    def test_find_project_root_walks_up_from_nested_path(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_workspace(root)
            nested = root / "agent_tools" / "tools" / "some_tool"
            nested.mkdir(parents=True)
            self.assertEqual(find_project_root(nested), root.resolve())

    def test_find_project_root_raises_without_markers(self) -> None:
        with TemporaryDirectory() as tmp:
            with self.assertRaises(RulesSyncError):
                find_project_root(Path(tmp))

    def test_discover_rules_reads_sync_mode_and_scope(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_workspace(root)
            rules = {rule.slug: rule for rule in discover_rules(root)}
            self.assertEqual(rules["always-one"].sync_mode, "always")
            self.assertEqual(rules["skill-covered"].sync_mode, "skill")
            self.assertEqual(rules["ignored"].sync_mode, "none")
            self.assertEqual(
                rules["skill-covered"].scope_sentence,
                "These rules apply to widget code.",
            )

    def test_discover_rules_rejects_missing_sync_field(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_workspace(root)
            _write(root / "agent_tools" / "rules" / "broken.md", "# Broken\n\nNo frontmatter.\n")
            rules = {rule.slug: rule for rule in discover_rules(root)}
            with self.assertRaises(RulesSyncError):
                _ = rules["broken"].sync_mode

    def test_discover_skills_reads_rule_backref(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_workspace(root)
            skills = {skill.name: skill for skill in discover_skills(root)}
            self.assertEqual(
                skills["widget-tool"].rule_backref,
                "agent_tools/rules/skill-covered.md",
            )
            self.assertIsNone(skills["standalone-tool"].rule_backref)


class RulesSyncPlanTests(unittest.TestCase):
    def test_plan_all_covers_mirrors_and_orphan_stub_and_skips_covered_and_none(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_workspace(root)
            outputs = plan_all(root)
            relative = {path.relative_to(root): content for path, content in outputs.items()}

            self.assertIn(Path(".claude/skills/widget-tool/SKILL.md"), relative)
            self.assertIn(Path(".claude/skills/standalone-tool/SKILL.md"), relative)
            # skill-covered has a paired skill, so no duplicate stub.
            self.assertNotIn(Path(".claude/skills/skill-covered/SKILL.md"), relative)
            # skill-orphan has no paired skill, so it gets an auto-generated stub.
            self.assertIn(Path(".claude/skills/skill-orphan/SKILL.md"), relative)
            # sync: none is never mirrored.
            self.assertNotIn(Path(".claude/skills/ignored/SKILL.md"), relative)

            widget_mirror = relative[Path(".claude/skills/widget-tool/SKILL.md")]
            self.assertIn("name: widget-tool", widget_mirror)
            self.assertIn("the agent should run the widget CLI", widget_mirror)
            self.assertNotIn("rule:", widget_mirror)

            orphan_stub = relative[Path(".claude/skills/skill-orphan/SKILL.md")]
            self.assertIn("agent_tools/rules/skill-orphan.md", orphan_stub)

            claude_md = relative[Path("CLAUDE.md")]
            self.assertIn("Always One", claude_md)
            self.assertIn("Do the thing.", claude_md)
            self.assertNotIn("Skill Covered", claude_md)

    def test_render_claude_always_block_only_includes_always_rules(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_workspace(root)
            block = render_claude_always_block(discover_rules(root))
            self.assertIn("Always One", block)
            self.assertNotIn("Skill Covered", block)
            self.assertNotIn("Ignored", block)


class RulesSyncApplyTests(unittest.TestCase):
    def test_apply_plan_check_only_does_not_write(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_workspace(root)
            claude_md_before = (root / "CLAUDE.md").read_text(encoding="utf-8")
            outputs = plan_all(root)
            result = apply_plan(outputs, check_only=True)
            self.assertFalse(result.is_clean)
            self.assertFalse((root / ".claude").exists())
            self.assertEqual((root / "CLAUDE.md").read_text(encoding="utf-8"), claude_md_before)

    def test_apply_plan_write_then_check_is_clean(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_workspace(root)
            outputs = plan_all(root)
            first = apply_plan(outputs, check_only=False)
            self.assertFalse(first.is_clean)

            second_outputs = plan_all(root)
            second = apply_plan(second_outputs, check_only=True)
            self.assertTrue(second.is_clean)
            self.assertEqual(len(second.unchanged), len(outputs))

    def test_apply_plan_is_idempotent_on_reruns(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_workspace(root)
            apply_plan(plan_all(root), check_only=False)
            before = {
                path: path.read_text(encoding="utf-8")
                for path in plan_all(root)
            }
            apply_plan(plan_all(root), check_only=False)
            after = {
                path: path.read_text(encoding="utf-8")
                for path in plan_all(root)
            }
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

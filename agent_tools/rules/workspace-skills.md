---
sync: skill
---

# Workspace skill workflow

These rules apply to Codex skills that support workspace-local tools,
environments, and recurring workflows.

1. Keep workspace-specific skills in `agent_tools/skills/<skill-name>/` with a
   required `SKILL.md`. Do not rely on a matching skill installed in
   `~/.codex/skills` for workspace workflows.
2. A workspace skill is an agent-facing workflow wrapper, not the home for
   reusable implementation. It should name the relevant Agent Workspace MCP
   tools first when the workflow has MCP coverage, and list
   `python -m agent_tools...` commands or scripts under `agent_tools/` as the
   fallback path. Do not assume external installation.
3. Keep reusable executable code in normal workspace tool or environment
   locations, for example `agent_tools/<tool_name>/` or
   `agent_tools/paf_workspace/domains/environments/`. Do not put executable
   implementation under `agent_tools/skills/<skill-name>/scripts/`.
4. Keep human/tool documentation in `README.md` files beside the reusable tool
   or environment. Do not add `README.md` inside skill directories; `SKILL.md`
   is the skill entry point.
5. When a workspace tool has mandatory policy, keep that policy in
   `agent_tools/rules/` and have the related skill point to the rule. The rule
   remains authoritative for all tasks, while the skill explains when and how
   to use the tool.
6. If a new recurring workspace workflow depends on an installed/global Codex
   skill, add or update a workspace-local `agent_tools/skills/` wrapper before
   treating the workflow as reusable.
7. Keep reusable PAF automation under `agent_tools/paf_workspace/domains/`.
   Model those directories as automation spheres: a domain may contain PAF task
   modules, runnable scenarios, target profiles, templates for task-local
   customization, and an `assets/` directory for non-PAF support code owned by
   that domain. Do not leave a repeatable build, orchestration, or test
   workflow only inside one task directory once it is useful for multiple
   tasks.
8. Use PAF as the default entry point for repeatable multi-stage validation.
   A task that must fetch or select sources, build Docker environments, build
   Moulin products, resolve artifacts, run a harness, and collect evidence
   should provide or reuse a PAF scenario/profile.
9. For Xen/QEMU validation, model runtime launch and log collection as PAF
   tasks inside the `xen-zephyr` domain. Keep runtime settings in the
   domain-specific YAML under `xen_zephyr.harness`; do not use task-owned shell
   wrappers or separate JSON scenario files for repeatable validation.
10. Put domain-owned support code that is not a PAF task under
   `agent_tools/paf_workspace/domains/<domain>/assets/`. Examples include
   Zephyr modules, Yocto layers, target-side helper sources, and fixtures.
   Keep PAF entry points in a domain `tasks/` package, plus `scenarios/`,
   `profiles/`, and `templates/`. Put Python implementation used by those
   tasks in the standard `lib/` package, not in ad hoc support directories.
11. `agent_tools/rules/*.md` and `agent_tools/skills/*/SKILL.md` are the single
   source of truth for both Codex and any other coding agent working in this
   workspace. Do not hand-maintain a second, agent-specific copy of this
   policy. Use `agent_tools/tools/rules_sync` to mirror it into other agents'
   native conventions (for example Claude Code's `.claude/skills/` and
   `CLAUDE.md`).

   Every file under `agent_tools/rules/` must start with a frontmatter block
   declaring how `rules_sync` mirrors it:

   ```text
   ---
   sync: always | skill | none
   ---
   ```

   - `always`: the rule applies to every task or every repository (matches the
     rule's own "These rules apply to ..." scope sentence having no
     condition). Its full body is mirrored into a generated, clearly marked
     block inside the other agent's always-loaded instructions file. Keep
     these rules short; their cost is paid on every session regardless of
     task.
   - `skill`: the rule is conditional. It is mirrored as a lazily-loaded skill
     for the other agent, generated either from a paired
     `agent_tools/skills/<name>/SKILL.md` (see the `rule:` backref below) or,
     if none exists yet, as a minimal stub built from the rule file itself.
   - `none`: do not mirror this file at all.

   A `SKILL.md` that fully wraps one `sync: skill` rule file must add a
   `rule: agent_tools/rules/<file>.md` field to its frontmatter. This tells
   `rules_sync` that the paired skill already covers the rule, so it must not
   also generate a duplicate stub for that rule file. Leave `rule:` out for
   skills that are not a full wrapper of one rule file.

   Every `agent_tools/skills/*/SKILL.md` is mirrored as-is (all of them, with
   no opt-out) into the other agent's native skill format, regardless of
   whether it carries a `rule:` backref.

   New rule files, new skill directories, and new tools are picked up
   automatically the next time `rules_sync` runs; nothing here needs to be
   hardcoded by filename. Only the frontmatter fields above need to be kept
   correct. Run `python -m agent_tools.tools.rules_sync sync --check` and fix
   any reported drift before treating a change under `agent_tools/rules/` or
   `agent_tools/skills/` as complete.

Use this routing table for common workspace task types:

```text
C/C++ source analysis or guarded edits -> cpp-code-map
Python source analysis or guarded edits -> python-code-map
YAML configuration edits -> yaml-map
Xen/QEMU runtime validation -> xen-qemu-harness
Multi-stage validation orchestration -> PAF plus xen-qemu-harness
Moulin CI or local workflow validation -> moulin-local-validation
Diff or patch review reports -> diff-review-report
Commit message formatting -> commit-message-format
Task layout and workflow metadata checks -> validate_task or task action
Task context, handoff notes, decisions, blockers, validation notes, or context
compaction -> task-context-journal
Mirroring rules/skills into another coding agent's native conventions ->
rules-sync
```

For Agent Workspace tool workflows, the skill should prefer these MCP names
when available:

```text
Python source maps/edits -> code_map_*
C/C++ source maps/edits -> cpp_light_* or cpp_code_map_*
YAML maps/edits -> yaml_map_*
Diff reports -> diff_report_*
Commit message formatting -> commit_msg_format
Task actions -> task_actions_*
Task context -> task_context_*
Task repo registry -> repo_registry_*
Push validation stamps/hooks -> push_guard_* and workspace_validate
Repository validation policy -> workspace_validate, validate_changed,
validate_task, workspace_validation_policy, workspace_validation_status
Compact workspace search -> agent_search_*
```

When more than one row applies, read the rules first, then the minimal matching
skills needed for the task.

# Workspace skill workflow

These rules apply to Codex skills that support workspace-local tools,
environments, and recurring workflows.

1. Keep workspace-specific skills in `codex_tools/skills/<skill-name>/` with a
   required `SKILL.md`. Do not rely on a matching skill installed in
   `~/.codex/skills` for workspace workflows.
2. A workspace skill is an agent-facing workflow wrapper, not the home for
   reusable implementation. It should reference the checked-in workspace
   implementation, such as `python -m codex_tools...` or scripts under
   `codex_tools/`, instead of assuming external installation.
3. Keep reusable executable code in normal workspace tool or environment
   locations, for example `codex_tools/<tool_name>/` or
   `codex_tools/environments/<environment_name>/`. Do not put executable
   implementation under `codex_tools/skills/<skill-name>/scripts/`.
4. Keep human/tool documentation in `README.md` files beside the reusable tool
   or environment. Do not add `README.md` inside skill directories; `SKILL.md`
   is the skill entry point.
5. When a workspace tool has mandatory policy, keep that policy in
   `codex_tools/rules/` and have the related skill point to the rule. The rule
   remains authoritative for all tasks, while the skill explains when and how
   to use the tool.
6. If a new recurring workspace workflow depends on an installed/global Codex
   skill, add or update a workspace-local `codex_tools/skills/` wrapper before
   treating the workflow as reusable.

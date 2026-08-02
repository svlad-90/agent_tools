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
   `codex_tools/paf_workspace/domains/environments/`. Do not put executable
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
7. Keep reusable PAF automation under `codex_tools/paf_workspace/domains/`.
   Model those directories as automation spheres, similar to the historical
   `/home/vladyslav_goncharuk/Projects/tools/aasig_dev_platform/build/`
   layout: a domain may contain PAF task modules, runnable scenarios, target
   profiles, templates for task-local customization, and an `assets/`
   directory for non-PAF support code owned by that domain. Do not leave a
   repeatable build, orchestration, or test workflow only inside one task
   directory once it is useful for multiple tasks.
8. Use PAF as the default entry point for repeatable multi-stage validation.
   A task that must fetch or select sources, build Docker environments, build
   Moulin products, resolve artifacts, run a harness, and collect evidence
   should provide or reuse a PAF scenario/profile.
9. For Xen/QEMU validation, model runtime launch and log collection as PAF
   tasks inside the `xen-zephyr` domain. Keep runtime settings in the
   domain-specific YAML under `xen_zephyr.harness`; do not use task-owned shell
   wrappers or separate JSON scenario files for repeatable validation.
10. Put domain-owned support code that is not a PAF task under
   `codex_tools/paf_workspace/domains/<domain>/assets/`. Examples include
   Zephyr modules, Yocto layers, target-side helper sources, and fixtures.
   Keep PAF entry points in `tasks.py` or a `tasks/` package, plus
   `scenarios/`, `profiles/`, and `templates/`. Put Python implementation used
   by those tasks in the standard `lib/` package, not in ad hoc support
   directories.

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
Task layout and workflow metadata checks -> python -m codex_tools.task_check
```

When more than one row applies, read the rules first, then the minimal matching
skills needed for the task.

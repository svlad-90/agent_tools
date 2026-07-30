# Workspace Knowledge

This directory stores recurring findings that are likely to matter across more
than one task. Use it for durable, topic-specific knowledge, not for ordinary
task notes, guesses, or one-off debugging history.

Before starting a task, identify the task topics and read the matching files
under `topics/`. Treat each finding as a checklist prompt: it may save time,
but it is not proof that the same root cause applies.

## Topic Routing

```text
Xen, Zephyr Dom0/DomU, QEMU runtime, XenStore, hypercalls -> topics/xen.md
codex_tools, workspace tools, task_check, diff_report, code maps -> topics/codex_tools.md
Moulin products, Moulin CI, product builds, generated runtime artifacts -> topics/moulin.md
```

If a task spans several topics, read every matching topic file before deep
diagnostics, implementation, validation, or report work.

## Adding Findings

Add a finding only when it is important enough to help future tasks. Prefer
topic files over a global scratchpad.

Each finding should include:

- the condition where it applies;
- the failure shape or misleading symptom;
- the practical checklist or command that avoids repeating the investigation;
- exact versions, commits, paths, or symbols when they are essential.

If no existing topic fits, create `topics/<topic>.md` and add a routing entry
above.

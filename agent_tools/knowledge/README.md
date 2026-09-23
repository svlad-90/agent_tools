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
agent_tools, workspace tools, task_check, diff_report, code maps -> topics/agent_tools.md
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

## Local Knowledge Database

The markdown topic files remain the reviewable public knowledge source. The
`agent_tools.tools.knowledge` CLI also supports a local SQLite database for
more structured private findings:

```sh
python -m agent_tools.tools.knowledge db-init
python -m agent_tools.tools.knowledge db-add agent_tools "repo_guard owns validation policy" --tag validation
python -m agent_tools.tools.knowledge db-search validation
python -m agent_tools.tools.knowledge db-get 1
python -m agent_tools.tools.knowledge db-topics
```

By default the database lives under `knowledge/private/knowledge.sqlite3`,
which is intentionally private workspace state. Set `AGENT_TOOLS_KNOWLEDGE_DB`
to use another path. Use `--scope public` only for entries that can safely be
promoted to tracked markdown later.

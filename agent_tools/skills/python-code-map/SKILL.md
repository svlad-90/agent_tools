---
name: python-code-map
description: Navigate, inspect, safely edit, validate, and audit Python source files with the workspace agent_tools.tools.code_map AST-based tool. Use when Codex works on Python code, needs symbol maps, guarded function/class edits, import insertion, batch edits, parse-check validation, class diagrams, facade audits, or protocol audits.
---

# Python Code Map

Use the workspace implementation at `agent_tools/tools/code_map`. Do not depend on a
globally installed Codex skill for this workflow.

Also follow `agent_tools/rules/python-code.md`; that rule is authoritative for
workspace Python work.

## Core Workflow

Run commands from the workspace root or another directory where `agent_tools`
is importable:

```sh
python -m agent_tools.tools.code_map <command> ...
```

Before reading or changing a Python file, inspect its symbol map:

```sh
python -m agent_tools.tools.code_map map path/to/file.py
```

Before changing a function, method, class, or other symbol, get a guarded
snapshot:

```sh
python -m agent_tools.tools.code_map symbol-get path/to/file.py \
  --symbol QualifiedName --json
```

Use `hash` for whole-symbol edits and `body_hash` for body-only edits.

## Guarded Edits

Prefer guarded edits when replacing or inserting Python code:

```sh
python -m agent_tools.tools.code_map replace-symbol-body path/to/file.py \
  --symbol function_name \
  --expect-hash <body_hash> \
  --replacement-file /tmp/replacement.py
```

Use `imports-add` for imports so duplicate imports are not introduced:

```sh
python -m agent_tools.tools.code_map imports-add path/to/file.py \
  --import 'from pathlib import Path'
```

Use `--check-only` first for risky edits or broad files.

## Validation

After every Python edit, run:

```sh
python -m agent_tools.tools.code_map parse-check path/to/file.py
```

For larger Python design work, use `class-diagram`, `facade-audit`, or
`protocol-audit` when they match the local architecture question.

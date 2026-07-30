---
name: cpp-code-map
description: Navigate, inspect, safely edit, and audit C/C++ source files with the workspace codex_tools.cpp_code_map libclang-based tool. Use when Codex works on C or C++ code, needs exact symbol maps, guarded symbol/body edits, compile_commands.json based parsing, include insertion, batch edits, or DMA_Plantuml puml-audit checks in the real build environment.
---

# C++ Code Map

Use the workspace implementation at `codex_tools/cpp_code_map`. Do not depend
on a globally installed Codex skill for this workflow.

Also follow `codex_tools/rules/cpp-code.md`; that rule is stricter than this
skill for workspace C/C++ work, especially for Docker, Zephyr, generated
headers, and real build environments.

## Core Workflow

Run commands from the repository or workspace root where `codex_tools` is
importable:

```sh
python -m codex_tools.cpp_code_map <command> ...
```

Prefer a real compile database:

```sh
python -m codex_tools.cpp_code_map map path/to/file.c --compile-db path/to/build
```

For CMake projects, generate one first when missing:

```sh
cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
```

For projects where a component is not standalone, configure the real parent
project that defines the needed CMake functions, generated headers, sysroots,
module paths, and toolchain settings.

## Inspect Before Editing

Before reading or changing a C/C++ file, inspect its symbol map:

```sh
python -m codex_tools.cpp_code_map map path/to/file.c --compile-db build
```

Before changing a symbol, get a guarded snapshot:

```sh
python -m codex_tools.cpp_code_map symbol-get path/to/file.c \
  --symbol function_or_Class::method --compile-db build --json
```

Use `hash` for whole-symbol edits and `body_hash` for body-only edits.

## Guarded Edits

Prefer guarded edits when replacing or inserting code so stale snapshots fail
before writing:

```sh
python -m codex_tools.cpp_code_map replace-symbol-body path/to/file.c \
  --symbol function_name \
  --expect-hash <body_hash> \
  --replacement-text $'\n\treturn 0;\n' \
  --compile-db build
```

Use `--check-only` first for risky edits or large translation units.

## Fast Parse Feedback

Use parse-check when it gives useful fast feedback in the same build
environment:

```sh
python -m codex_tools.cpp_code_map parse-check path/to/file.c --compile-db build
```

If parsing fails, fix the build context before treating diagnostics as
meaningful. Use `--clang-arg` only as a targeted fallback when the compile
database is unavailable or incomplete.

For Docker or cross builds, run `cpp_code_map` inside the same environment that
created `compile_commands.json` so compiler paths, generated headers, sysroots,
and module paths exist.

The authoritative validation remains the project's normal build, test, or
runtime workflow. `parse-check` does not replace that validation.

## DMA_Plantuml Audit

For projects using `DMA_Plantuml`, use `puml-audit` instead of generating an
independent class diagram:

```sh
python -m codex_tools.cpp_code_map puml-audit path/to/file.cpp --compile-db build
```

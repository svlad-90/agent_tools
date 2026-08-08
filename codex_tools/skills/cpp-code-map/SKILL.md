---
name: cpp-code-map
description: Navigate, inspect, safely edit, and audit C/C++ source files with the workspace codex_tools.tools.cpp_code_map libclang-based tool. Use when Codex works on C or C++ code, needs exact symbol maps, guarded symbol/body edits, compile_commands.json based parsing, include insertion, batch edits, or DMA_Plantuml puml-audit checks in the real build environment.
---

# C++ Code Map

Use the workspace implementations at `codex_tools/tools/cpp_light_code_map` and
`codex_tools/tools/cpp_code_map`. Do not depend on a globally installed Codex
skill for this workflow.

Also follow `codex_tools/rules/cpp-code.md`; that rule is stricter than this
skill for workspace C/C++ work, especially for Docker, Zephyr, generated
headers, and real build environments.

## Core Workflow

Use `cpp_light_code_map` first when the build environment is not yet
formalized: the checkout, generated headers, container, toolchain, or compile
database are still being discovered. It is the normal first-pass tool for
orientation and quick structural edits:

```sh
python -m codex_tools.tools.cpp_light_code_map diagnose path/to/file.c --json
python -m codex_tools.tools.cpp_light_code_map outline path/to/file.c --compact
python -m codex_tools.tools.cpp_light_code_map symbols path/to/file.c --kind function --json
```

Use `cpp_code_map` once the build context is stable enough for exact source
analysis:

Run commands from the repository or workspace root where `codex_tools` is
importable:

```sh
python -m codex_tools.tools.cpp_code_map <command> ...
```

Prefer a real compile database:

```sh
python -m codex_tools.tools.cpp_code_map map path/to/file.c --compile-db path/to/build
```

For CMake projects, generate one first when missing:

```sh
cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
```

For projects where a component is not standalone, configure the real parent
project that defines the needed CMake functions, generated headers, sysroots,
module paths, and toolchain settings.

## Inspect Before Editing

Before first-pass reading or quick structural edits, inspect the file with the
light map:

```sh
python -m codex_tools.tools.cpp_light_code_map diagnose path/to/file.c --json
python -m codex_tools.tools.cpp_light_code_map outline path/to/file.c --compact
```

Before precise edits in a stable build environment, inspect its build-backed
symbol map:

```sh
python -m codex_tools.tools.cpp_code_map map path/to/file.c --compile-db build
```

When `--compile-db` is provided, run `doctor` first if the environment is new,
containerized, or suspicious:

```sh
python -m codex_tools.tools.cpp_code_map doctor path/to/file.c --compile-db build --json
```

The doctor explains source visibility, compile database resolution, matched
entry, compiler, include/sysroot paths, selected clang arguments, and whether a
fallback was used. If `--compile-db` is provided but the file has no matching
entry, `cpp_code_map` fails instead of silently using generic clang arguments;
pass `--allow-fallback` only when a structural/rough parse is intentionally
acceptable.

Before changing a symbol, get a guarded snapshot:

```sh
python -m codex_tools.tools.cpp_code_map symbol-get path/to/file.c \
  --symbol function_or_Class::method --compile-db build --json
```

Use `hash` for whole-symbol edits and `body_hash` for body-only edits.

## Guarded Edits

Prefer guarded edits when replacing or inserting code so stale snapshots fail
before writing:

```sh
python -m codex_tools.tools.cpp_code_map replace-symbol-body path/to/file.c \
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
python -m codex_tools.tools.cpp_code_map parse-check path/to/file.c --compile-db build
```

If parsing fails, fix the build context before treating diagnostics as
meaningful. Use `--clang-arg` only as a targeted fallback when the compile
database is unavailable or incomplete.

For Docker or cross builds, run `cpp_code_map` inside the same environment that
created `compile_commands.json` so compiler paths, generated headers, sysroots,
and module paths exist.

For workspace Docker-backed environments, run the reusable PAF preflight before
relying on C/C++ source analysis:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/environments/scenarios/cpp-code-map.xml \
  check-only \
  --yaml-config codex_tools/paf_workspace/domains/environments/profiles/cpp-code-map-zephyr-xen.yaml \
  --parameter CPP_CODE_MAP_SOURCE=path/to/file.c \
  --parameter CPP_CODE_MAP_COMPILE_DB=path/to/build \
  --parameter CPP_CODE_MAP_REPORT=report/cpp-code-map-preflight.json
```

The preflight remaps workspace-relative or host-absolute paths into the
container mount, checks that `clang.cindex` and `codex_tools` import inside the
container, validates the compile database entry and referenced paths, and then
runs `map` plus `parse-check`. If it fails in `image_check`, build or ensure the
declared environment image before debugging source parsing.

The authoritative validation remains the project's normal build, test, or
runtime workflow. `parse-check` does not replace that validation.

## Build-Free Structural Map

When the build environment or compile database is not yet stable, use the
structural map as the main navigation tool for early work:

```sh
python -m codex_tools.tools.cpp_light_code_map map path/to/file.c
python -m codex_tools.tools.cpp_light_code_map symbol-get path/to/file.c --symbol name --json
```

`cpp_light_code_map` requires `tree-sitter` and `tree-sitter-cpp`. It does not
use libclang, does not validate types, and does not prove compilation. Treat
its output as `structural-only`. Once the environment is settled, promote exact
analysis and guarded C/C++ edits to `cpp_code_map`.

Use it for fast orientation, early estimates, and quick structural fixes:

```sh
python -m codex_tools.tools.cpp_light_code_map outline path/to/file.c --compact
python -m codex_tools.tools.cpp_light_code_map diagnose path/to/file.c --json
python -m codex_tools.tools.cpp_light_code_map unmapped path/to/file.c --json
python -m codex_tools.tools.cpp_light_code_map symbols path/to/file.c --kind function --name init
python -m codex_tools.tools.cpp_light_code_map includes path/to/file.c --json
python -m codex_tools.tools.cpp_light_code_map macros path/to/file.c --json
python -m codex_tools.tools.cpp_light_code_map calls path/to/file.c --symbol function_name --json
python -m codex_tools.tools.cpp_light_code_map call-graph path/to/file.c --json
python -m codex_tools.tools.cpp_light_code_map refs path/to/file.c --name identifier --scope function_name --json
python -m codex_tools.tools.cpp_light_code_map locals path/to/file.c --symbol function_name --json
python -m codex_tools.tools.cpp_light_code_map complexity path/to/file.c --symbol function_name --json
```

For repeated workspace navigation, cache structural symbol maps and query them:

```sh
python -m codex_tools.tools.cpp_light_code_map index src/a.c src/b.cpp --cache-dir /tmp/cpp-light-index
python -m codex_tools.tools.cpp_light_code_map index-dir src --include '*.c' --include '*.cpp' --cache-dir /tmp/cpp-light-index
python -m codex_tools.tools.cpp_light_code_map query --name symbol --cache-dir /tmp/cpp-light-index
```

For edits, prefer `--check-only` first and use the hash returned by
`symbol-get`:

```sh
python -m codex_tools.tools.cpp_light_code_map replace-symbol-body path/to/file.c \
  --symbol function_name --expect-hash <body_hash> --replacement-text $'\n\treturn 0;\n' --check-only
python -m codex_tools.tools.cpp_light_code_map rename-symbol path/to/file.c \
  --symbol function_name --expect-hash <hash> --new-name new_name --check-only
```

## DMA_Plantuml Audit

For projects using `DMA_Plantuml`, use `puml-audit` instead of generating an
independent class diagram:

```sh
python -m codex_tools.tools.cpp_code_map puml-audit path/to/file.cpp --compile-db build
```

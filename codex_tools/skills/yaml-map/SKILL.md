---
name: yaml-map
description: Inspect, query, safely edit, and validate YAML files with the workspace codex_tools.tools.yaml_map structured YAML tool. Use when Codex works on YAML configuration, GitHub Actions workflows, Zephyr metadata, module.yml files, CI manifests, Docker-compose files, or other YAML where path-based edits and parse-check validation are safer than ad hoc text edits.
---

# YAML Map

Use the workspace implementation at `codex_tools/tools/yaml_map`. Do not depend on a
globally installed Codex skill for this workflow.

Use this skill for structured YAML work where preserving valid YAML and editing
the intended path matters more than raw text replacement.

## Core Workflow

Run commands from the workspace root or another directory where `codex_tools`
is importable:

```sh
python -m codex_tools.tools.yaml_map <command> ...
```

Inspect a YAML file before editing:

```sh
python -m codex_tools.tools.yaml_map map path/to/file.yml
```

For broader discovery, inspect a project:

```sh
python -m codex_tools.tools.yaml_map project-map path/to/project --deep
```

Read a specific path before changing it:

```sh
python -m codex_tools.tools.yaml_map path-get path/to/file.yml \
  --path build.settings
```

## Guarded Edits

Use the hash from `map` or `path-get` for guarded path updates:

```sh
python -m codex_tools.tools.yaml_map path-set path/to/file.yml \
  --path build.settings.board_root \
  --expect-hash <hash> \
  --value-json '".'"
```

Insert list or mapping items with `item-insert`:

```sh
python -m codex_tools.tools.yaml_map item-insert path/to/file.yml \
  --path jobs.build.steps \
  --index 0 \
  --expect-hash <hash> \
  --value-file /tmp/step.json
```

Use `--check-only` first for risky edits.

## Validation

After every YAML edit, run:

```sh
python -m codex_tools.tools.yaml_map parse-check path/to/file.yml
```

If a YAML format relies on comments or unusual formatting that the structured
tool cannot preserve, report that limitation and use the narrowest manual edit.

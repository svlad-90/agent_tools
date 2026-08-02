# PAF Workspace Assets

This directory contains workspace-owned PAF automation assets. PAF itself is
kept as an external framework and is fetched by `run-paf.sh` when needed.
The default checked-out PAF revision is
`7b84022dfff93a9bc7f643a5d74bd2d06f457bb4`, the current workspace-validated
baseline with full repository mypy coverage for PAF's core, CLI entry point,
and tests. Override it with `PAF_REF` only when a task intentionally validates
a different PAF revision.
Existing cached PAF checkouts are reused; set `PAF_UPDATE=1` when the wrapper
must fetch and checkout `PAF_REF` again.

The purpose of this directory is to collect reusable automation work in the
same spirit as `/home/vladyslav_goncharuk/Projects/tools/aasig_dev_platform/build/`:
separate automation domains keep their own scenarios, profiles, templates, and
task modules for typical recurring work.

## Layout

```text
run-paf.sh              # generic workspace entry point for PAF
tasks.py                # generic base task helpers, not domain workflows
domains/
  <domain>/
    README.md           # domain scope and supported flows
    tasks/              # mandatory package for domain-owned PAF task classes
    domain.yaml         # optional domain metadata and defaults
    schema.yaml         # optional domain YAML schema
    scenarios/          # runnable PAF XML scenarios
    profiles/           # reusable case/profile presets for target variants
    templates/          # starting points for task-local customization
```

Use domains for recurring areas of work, for example:

- `xen-zephyr` for Xen, Zephyr, zephyr-xenlib, Moulin, QEMU, Dom0, and DomU
  build/run/test flows;
- `moulin` for Moulin product build orchestration that is not tied to Xen;
- `ci` for GitHub Actions or `act` wrapper flows;
- `reports` for repeated report generation or publication flows.

Task-local scenario files may still live under the task directory while a flow
is being developed. Once the same shape is useful for more than one task, move
the reusable version here and keep only task-specific overrides in the task.

## PAF-First Validation

Use PAF as the outer entry point for repeatable validation. A domain scenario
should own environment selection/checks, product build commands, artifact
manifests, runtime task phases, and generated evidence. Runtime launch
descriptions should be domain YAML, not separate shell scripts.

Minimal smoke for the Xen/Zephyr domain:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/xen_zephyr/scenarios/build-run-harness.xml \
  check-only \
  --yaml-config codex_tools/paf_workspace/domains/xen_zephyr/profiles/check-only.yaml \
  --parameter PRODUCT_DIR=.
```

This validates PAF checkout discovery, workspace task imports, Xen/Zephyr
domain discovery, YAML schema validation, and domain default projection without
building a product or starting QEMU.

When a task uses the PAF Docker helpers, PAF expands the container alias to the
actual `docker run ... /bin/bash -lc <command>` invocation and logs it through
the same subprocess command and command-after-substitution output used for
host commands. Use the normal `avoid_printing_command` flags only when the
command text itself is sensitive.

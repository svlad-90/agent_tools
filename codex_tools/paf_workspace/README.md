# PAF Workspace Assets

This directory contains workspace-owned PAF automation assets. PAF itself is
kept as an external framework and is fetched by `run-paf.sh` when needed.
The default checked-out PAF revision is
`7b84022dfff93a9bc7f643a5d74bd2d06f457bb4`, the current workspace-validated
baseline with full repository mypy coverage for PAF's core, CLI entry point,
and tests. Override it with `PAF_REF` only when a task intentionally validates
a different PAF revision.

The purpose of this directory is to collect reusable automation work in the
same spirit as `/home/vladyslav_goncharuk/Projects/tools/aasig_dev_platform/build/`:
separate automation domains keep their own scenarios, profiles, templates, and
task modules for typical recurring work.

## Layout

```text
run-paf.sh              # generic workspace entry point for PAF
tasks.py                # generic task classes shared by multiple domains
xen_zephyr/             # importable task namespace for the xen-zephyr domain
domains/
  <domain>/
    README.md           # domain scope and supported flows
    scenarios/          # runnable PAF XML scenarios
    profiles/           # XML fragments or scenario configs for target variants
    templates/          # starting points for task-local scenarios
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
should own environment checks, product build commands, artifact manifests,
runtime harness invocation, and generated evidence. Lower-level tools such as
`codex_tools/xen_harness/scripts/run-scenario.sh` remain useful runtime
executors, but direct calls are for narrow debug steps. Once the command shape
is reused, promote it into a PAF domain scenario or profile.

Minimal smoke for the Xen/Zephyr domain:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/xen-zephyr/scenarios/build-run-harness.xml \
  check-only \
  --yaml-config codex_tools/paf_workspace/domains/xen-zephyr/profiles/check-only.yaml \
  --parameter PRODUCT_DIR=. \
  --parameter HARNESS_CMD=true
```

This validates PAF checkout discovery, workspace task imports, Xen/Zephyr
domain discovery, YAML schema validation, and domain default projection without
building a product or starting QEMU.

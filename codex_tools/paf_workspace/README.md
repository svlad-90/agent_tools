# PAF Workspace Assets

This directory contains workspace-owned PAF automation assets. PAF itself is
kept as an external framework and is fetched by `run-paf.sh` when needed.

The purpose of this directory is to collect reusable automation work in the
same spirit as `/home/vladyslav_goncharuk/Projects/tools/aasig_dev_platform/build/`:
separate automation domains keep their own scenarios, profiles, templates, and
task modules for typical recurring work.

## Layout

```text
run-paf.sh              # generic workspace entry point for PAF
tasks.py                # generic task classes shared by multiple domains
domains/
  <domain>/
    README.md           # domain scope and supported flows
    tasks.py            # optional domain-specific PAF task classes
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

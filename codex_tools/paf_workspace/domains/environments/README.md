# Environments PAF Domain

This domain owns reusable execution substrates: Docker images, container
aliases, toolchain smoke checks, and build commands that are shared by product
domains. Product domains should reference container aliases from this domain
instead of calling shell scripts under `codex_tools/environments`.

The domain exposes:

```text
tasks.py      PAF task classes
lib/          Python command builders used by tasks
assets/       Dockerfiles and environment source assets
scenarios/    runnable environment checks
profiles/     reusable environment YAML profiles
```

Environment entries:

- `zephyr-xen` provides a Zephyr SDK, west, CMake, Ninja, QEMU, and Python
  clang bindings. The default container alias is `zephyr-xen-workspace`, with
  the host workspace mounted at `/home/builder/workspace`.
- `codex-tools-act` provides an act driver image for running this repository's
  GitHub Actions workflows locally. It mounts the host Docker socket and the
  workspace.
- `moulin-act` provides the `ubuntu-22.04` act runner image used by Moulin's
  build workflow.
- `zephyr-xenlib-act` provides the `ubuntu-22.04` act runner image used by the
  zephyr-xenlib build workflow.

Run a check-only scenario with:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/environments/scenarios/<environment>.xml \
  check-only \
  --yaml-config codex_tools/paf_workspace/domains/environments/profiles/<environment>.yaml
```

Run validation with the same scenario and profile, replacing `check-only` with
`validate`. Use PAF `--parameter KEY=VALUE` overrides for task-local checkout
paths, token files, target filters, and extra act arguments.

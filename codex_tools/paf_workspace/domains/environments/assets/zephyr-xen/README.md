# Zephyr/Xen Environment Asset

This directory contains the Dockerfile used by the PAF `environments` domain
for the `zephyr-xen` image. It is an asset, not an execution entry point.

Use the PAF domain tasks instead of shell scripts:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/environments/scenarios/zephyr-xen.xml \
  check-only \
  --yaml-config codex_tools/paf_workspace/domains/environments/profiles/zephyr-xen.yaml
```

To validate a Zephyr build through the environment domain:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/environments/scenarios/zephyr-xen.xml \
  validate \
  --yaml-config codex_tools/paf_workspace/domains/environments/profiles/zephyr-xen.yaml \
  --parameter ZEPHYR_BUILD_ZEPHYR=zephyr-hypercalls/dev/zephyr-xen-hypercalls \
  --parameter ZEPHYR_BUILD_APP=samples/drivers/watchdog \
  --parameter ZEPHYR_BUILD_BOARD=xenvm \
  --parameter ZEPHYR_BUILD_DIR=build-pr136-wdt-cppmap
```

To validate Zephyr Doxygen coverage JSON generation through the same
environment domain:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/environments/scenarios/zephyr-docs.xml \
  validate \
  --yaml-config codex_tools/paf_workspace/domains/environments/profiles/zephyr-xen.yaml \
  --parameter ENVIRONMENT_FORCE_IMAGE_REBUILD=1 \
  --parameter ZEPHYR_DOCS_ZEPHYR=path/to/zephyr \
  --parameter ZEPHYR_DOCS_BUILD_DIR=/tmp/zephyr-doc-doxygen-coverage \
  --parameter ZEPHYR_DOCS_TIMEOUT_SEC=1800
```

Use the docs scenario for PR failures from
`.github/workflows/doxygen-coverage-delta.yml`, especially reports like
`file 'sched.h' is missing Doxygen comments`. The scenario requires the
`zephyr-xen` image built from this Dockerfile, including Doxygen, Graphviz, and
Zephyr documentation Python requirements.

The default container alias is `zephyr-xen-workspace`. It mounts the workspace
at `/home/builder/workspace`, so paths passed to validation tasks are
workspace-relative.

For standalone Zephyr checkouts that are not inside a west workspace, keep the
same validation scenario and select the direct CMake/Ninja mode:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/environments/scenarios/zephyr-xen.xml \
  validate \
  --yaml-config codex_tools/paf_workspace/domains/environments/profiles/zephyr-xen.yaml \
  --parameter ZEPHYR_BUILD_ZEPHYR=zephyr-hypercalls/dev/zephyr-xen-hypercalls \
  --parameter ZEPHYR_BUILD_APP=../pr148-sched-smoke \
  --parameter ZEPHYR_BUILD_BOARD=qemu_cortex_a53/qemu_cortex_a53 \
  --parameter ZEPHYR_BUILD_DIR=build-pr148-sched-smoke \
  --parameter ZEPHYR_BUILD_MODE=cmake \
  --parameter ZEPHYR_BUILD_BOARD_ROOTS=/home/builder/workspace/zephyr-hypercalls/dev/zephyr-xen-hypercalls \
  --parameter ZEPHYR_BUILD_MODULES=/home/builder/workspace/zephyr-hypercalls/dev/modules/lib/zephyr-xenlib \
  --parameter ZEPHYR_BUILD_KCONFIG_OPTIONS=CONFIG_XEN_WDT_FAIL_CHANNEL:0 \
  --parameter ZEPHYR_BUILD_EXPORT_COMPILE_COMMANDS=True \
  --parameter PUSH_GUARD_REPO=zephyr-hypercalls/dev/zephyr-xen-hypercalls \
  --parameter "PUSH_GUARD_SOURCE=zephyr-xen PAF validate"
```

Use newline-separated values for `ZEPHYR_BUILD_BOARD_ROOTS` or
`ZEPHYR_BUILD_MODULES` when a build needs more than one path. Use
newline-separated values for `ZEPHYR_BUILD_KCONFIG_OPTIONS` when a build needs
more than one Kconfig override. CLI parameters that contain Kconfig assignments
should use `CONFIG_NAME:value`; YAML profiles may use either `CONFIG_NAME=value`
or `CONFIG_NAME: value`. The task converts paths to Zephyr's semicolon-separated
CMake list format and Kconfig overrides to `-DCONFIG_NAME=value` inside the
container. When `PUSH_GUARD_REPO` is set, the scenario records a push_guard
stamp only after the Zephyr build task succeeds.

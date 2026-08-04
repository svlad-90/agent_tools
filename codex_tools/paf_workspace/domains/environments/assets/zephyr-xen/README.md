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
  --parameter ZEPHYR_BUILD_EXPORT_COMPILE_COMMANDS=True \
  --parameter PUSH_GUARD_REPO=zephyr-hypercalls/dev/zephyr-xen-hypercalls \
  --parameter "PUSH_GUARD_SOURCE=zephyr-xen PAF validate"
```

Use newline-separated values for `ZEPHYR_BUILD_BOARD_ROOTS` or
`ZEPHYR_BUILD_MODULES` when a build needs more than one path. The task converts
them to Zephyr's semicolon-separated CMake list format inside the container.
When `PUSH_GUARD_REPO` is set, the scenario records a push_guard stamp only
after the Zephyr build task succeeds.

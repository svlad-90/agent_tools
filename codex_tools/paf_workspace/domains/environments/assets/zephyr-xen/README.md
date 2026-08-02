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

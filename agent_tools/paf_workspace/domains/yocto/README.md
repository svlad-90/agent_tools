# Yocto PAF Domain

This domain provides reusable PAF tasks for running BitBake in a selected Yocto
workspace and Docker container.

The common scenario is:

```text
workspace_check -> ensure -> bitbake
```

`scenarios/bitbake.xml` defines these scenarios:

- `check-only`: validate workspace paths and YAML loading.
- `bitbake`: ensure the Yocto Docker image and run
  `bitbake <YOCTO_BITBAKE_ARGS>`.
- `target-build`: ensure the Yocto Docker image and run
  `bitbake <YOCTO_TARGET>`.
- `target-clean`: ensure the Yocto Docker image and run
  `bitbake -c <YOCTO_CLEAN_TASK> <YOCTO_TARGET>`.
- `target-graph`: ensure the Yocto Docker image, run
  `bitbake -g <YOCTO_TARGET>`, and optionally copy graph files to
  `YOCTO_GRAPH_OUTPUT_DIR`.

Parameters:

```text
YOCTO_DIR
YOCTO_INIT_SCRIPT
YOCTO_BUILD_DIR
YOCTO_CONTAINER_ALIAS
YOCTO_BITBAKE_ARGS
YOCTO_BITBAKE_TIMEOUT_SEC
YOCTO_TARGET
YOCTO_CLEAN_TASK
YOCTO_GRAPH_OUTPUT_DIR
YOCTO_GRAPH_LABEL
YOCTO_GRAPH_FILES
```

`YOCTO_DIR` is the directory where the init script is reachable. It defaults to
`${PRODUCT_DIR}/yocto` when `PRODUCT_DIR` is set. `YOCTO_INIT_SCRIPT` defaults
to `poky/oe-init-build-env`, `YOCTO_BUILD_DIR` defaults to
`build-xen-qemu-421`, and `YOCTO_CONTAINER_ALIAS` defaults to
`yocto-xen-workspace`. The default scenario image alias is `yocto-xen`; override
`ENVIRONMENT_IMAGE_ALIAS` when a task profile uses a different Docker image
alias.

The stable project-specific settings can also live in YAML:

```yaml
case:
  name: product-yocto
  domain: yocto
  workspace: .

yocto:
  directory: zephyr-blkfront-pv-disk/dev/qemu-xen-linux-service-zephyr-domu-validation/yocto
  build_dir: build-xen-qemu-421
  init_script: poky/oe-init-build-env
  container: yocto-xen-workspace
```

Examples:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/yocto/scenarios/bitbake.xml \
  bitbake \
  --yaml-config agent_tools/paf_workspace/domains/yocto/profiles/check-only.yaml \
  --parameter PRODUCT_DIR=zephyr-blkfront-pv-disk/dev/qemu-xen-linux-service-zephyr-domu-validation \
  --parameter YOCTO_BITBAKE_ARGS="xen-tools"

agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/yocto/scenarios/bitbake.xml \
  target-clean \
  --yaml-config agent_tools/paf_workspace/domains/yocto/profiles/check-only.yaml \
  --parameter PRODUCT_DIR=zephyr-blkfront-pv-disk/dev/qemu-xen-linux-service-zephyr-domu-validation \
  --parameter YOCTO_TARGET=xen-tools \
  --parameter YOCTO_CLEAN_TASK=clean

agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/yocto/scenarios/bitbake.xml \
  target-graph \
  --yaml-config agent_tools/paf_workspace/domains/yocto/profiles/check-only.yaml \
  --parameter PRODUCT_DIR=zephyr-blkfront-pv-disk/dev/qemu-xen-linux-service-zephyr-domu-validation \
  --parameter YOCTO_TARGET=xen-tools \
  --parameter YOCTO_GRAPH_OUTPUT_DIR=zephyr-blkfront-pv-disk/report/yocto-graphs
```

Task-local diagnostic wrappers can keep these PAF calls short while still
running through this domain. For the blkfront task, use:

```sh
zephyr-blkfront-pv-disk/scripts/yocto-paf.py clean xen-tools
zephyr-blkfront-pv-disk/scripts/yocto-paf.py graph xen-tools
zephyr-blkfront-pv-disk/scripts/yocto-paf.py analyze-graph \
  zephyr-blkfront-pv-disk/report/yocto-graphs/xen-tools
zephyr-blkfront-pv-disk/scripts/yocto-paf.py bitbake -- -e xen-tools
```

---
name: xen-qemu-harness
description: Run Xen/QEMU runtime checks through an externally supplied Docker runtime product while collecting raw, combined, Xen, Dom0, and DomU logs. Use when testing Zephyr or Xen changes that boot Xen with Dom0 and one or more DomU guests, need repeatable marker assertions across domains, or must keep samples free of test-only console workarounds.
---

# Xen QEMU Harness

Use this skill when a task needs Xen/QEMU runtime validation with logs from
more than one domain. Keep Zephyr samples and drivers on their normal logging
APIs (`printk()` or `LOG_*`). Domain log collection belongs in this harness or
in the runtime product, never in upstream sample code.

## Workflow

1. Build the Dom0/DomU images with the task's normal build scripts.
   For Zephyr Dom0 runtimes, enable the workspace extra module instead of
   copying collector code into the task:

   ```sh
   west build ... -- \
     -DZEPHYR_MODULES=/workspace/codex_tools/xen_harness/zephyr_module \
     -DOVERLAY_CONFIG=/workspace/codex_tools/xen_harness/zephyr_module/configs/dom0-console-collector.conf
   ```

   Use `ZEPHYR_MODULES` when the runtime build does not discover modules
   through west. Use `EXTRA_ZEPHYR_MODULES` only when west is already providing
   the normal module list and this module is an addition. The helper prints
   both modes:

   ```sh
   codex_tools/xen_harness/zephyr_module/scripts/zephyr-extra-module-args.sh
   ```

2. Run the bundled harness from the workspace root:

   ```sh
   python -m codex_tools.xen_harness.xen_qemu_harness \
     --out-dir task/report/runtime/name \
     --docker-image image-name:tag \
     --mount /host/runtime:/home/builder/workspace \
     --mount /home/user/workspace:/workspace \
     --docker-workdir /home/builder/workspace \
     --env QEMU_BIN=/path/in/container/qemu-system-aarch64 \
     --env DOMU_BIN=/workspace/task/dev/build/zephyr/zephyr.bin \
     --cmd 'bash ./scripts/gen-xen-dtb.sh /tmp/run.yaml >/dev/null && ./run/run-qemu.sh' \
     --expect xen:'Watchdog timer fired for domain 1'
   ```

3. Inspect generated logs in `--out-dir`:
   `raw.log`, `combined.log`, `xen.log`, `dom0.log`, `domu<N>.log`,
   `unknown.log`, and `summary.json`.

## Log Model

The harness always captures the complete process stdout/stderr as `raw.log`.
It then creates a best-effort split of the shared Xen serial stream:

- lines prefixed by `(XEN)` go to `xen.log`;
- Xen `Serial input to DOM<N>` notices update the active guest for following
  non-Xen serial lines;
- non-Xen lines go to the active guest log, or `unknown.log` when no active
  guest is known;
- `combined.log` prefixes every line with its inferred source.

This split is useful but not magic. If the runtime product does not expose a
DomU console on stdout or a separate file, DomU `printk()` markers will remain
absent. Treat that as a runtime/harness visibility issue, not a reason to add
`HYPERVISOR_console_io()` calls to the sample.

For Zephyr Dom0 validation products, DomU output must be collected by the
workspace Zephyr module under `codex_tools/xen_harness/zephyr_module`. The
module is the local equivalent of Linux Dom0 `xenconsoled`: it drains DomU Xen
PV console rings and emits domain-tagged lines that the host harness can split
into `domu<N>.log`. Runtime products should enable or disable the module by
configuration only.

When the runtime product can emit separate console files, pass them with
`--source name=/host/path.log`; those logs are copied into `--out-dir` and
included in marker checks.

## Assertions

Use `--expect source:text` for required markers. Sources are `raw`, `combined`,
`xen`, `dom0`, `domu1`, `unknown`, or a custom `--source` name. A missing
marker makes the harness exit non-zero after writing `summary.json`.

For manual Xen serial input switching, use `--xen-switch-at SECONDS`. The
harness writes the doubled QEMU stdio-mux escape sequence needed to deliver
three Ctrl-A bytes to Xen.

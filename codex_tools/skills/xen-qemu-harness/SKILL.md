---
name: xen-qemu-harness
description: Run Xen/QEMU runtime checks through an externally supplied Docker runtime product while streaming one domain-prefixed log. Use when testing Zephyr or Xen changes that boot Xen with Dom0 and one or more DomU guests, need live marker assertions across domains, or must keep samples free of test-only console workarounds.
---

# Xen QEMU Harness

Use this skill when a task needs Xen/QEMU runtime validation with logs from
more than one domain. Keep Zephyr samples and drivers on their normal logging
APIs (`printk()` or `LOG_*`). Domain log collection belongs in this harness or
in the runtime product, never in upstream sample code.

## Workflow

0. Follow the workspace Xen/Zephyr ABI rule before runtime debugging:
   `codex_tools/rules/xen-zephyr-abi.md`. The ABI check is mandatory before
   investigating XSM, FLASK labels, domids, magic pages, console rings, image
   loading, FDT generation, or hypercall behavior.

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

2. Run the bundled harness from the workspace root. Prefer task-owned scenario
   files for workspace validations:

   ```sh
   codex_tools/xen_harness/scripts/run-scenario.sh \
     task/scripts/xen-harness-scenarios/scenario-name.json
   ```

   A scenario file lives with the task, not in the harness. It can build the
   DomU image, normalize workspace paths, check Dom0/DomU image-size and
   load-address compatibility, check the Dom0 control ABI expected by the
   selected Xen/QEMU product, then run the one-log harness.

3. Use the reusable Zephyr/Xen preset directly only for one-off validation
   where a task scenario file would add more overhead than clarity:

   ```sh
   python -m codex_tools.xen_harness.xen_qemu_harness \
     --preset zephyr-xen-qemu \
     --timeout-sec 10 \
     --log-file task/report/runtime.log \
     --dom0-bin path/to/dom0/zephyr.bin \
     --domu-bin path/to/domu/zephyr.bin \
     --expect xen:'Watchdog timer fired for domain 1'
   ```

4. Inspect the generated `--log-file`. The harness streams this file while the
   process is running and stops the process early once all requested markers
   and required sources have been observed. Use `--no-stop-on-match` when the
   process must continue until it exits or reaches `--timeout-sec`.

## Log Model

The harness streams process stdout/stderr directly into the configured
`--log-file`. It does a best-effort classification for each line as it arrives:

- lines prefixed by `(XEN)` are tagged `[xen]`;
- QEMU or host process lines are tagged `[host]`;
- Xen `Serial input to DOM<N>` notices update the active guest for following
  non-Xen serial lines;
- lines emitted by the workspace Dom0 collector, such as
  `[xen-harness][domu1]`, are tagged from that embedded domain marker;
- non-Xen lines are tagged with the active guest, or `[unknown]` when no active
  guest is known.

This classification is useful but not magic. If the runtime product does not
expose a DomU console on stdout, DomU `printk()` markers will remain absent.
Treat that as a runtime/harness visibility issue, not a reason to add
`HYPERVISOR_console_io()` calls to the sample.

For Zephyr Dom0 validation products, DomU output must be collected by the
workspace Zephyr module under `codex_tools/xen_harness/zephyr_module`. The
module is the local equivalent of Linux Dom0 `xenconsoled`: it drains DomU Xen
PV console rings and emits domain-tagged lines that the host harness preserves
in the streamed combined log. Runtime products should enable or disable the
module by configuration only.

## Assertions

Use `--expect source:text` for required markers. Sources are `raw`, `combined`,
`host`, `xen`, `dom0`, `domu1`, or `unknown`. A missing marker makes the
harness exit non-zero after `--timeout-sec`.

Use `--require-source SOURCE` when the test must prove that a source log is
non-empty, for example `--require-source domu1`. This is useful for separating
"Xen observed the behavior" from "the harness can actually see DomU output".

For manual Xen serial input switching, use `--xen-switch-at SECONDS`. The
harness writes the doubled QEMU stdio-mux escape sequence needed to deliver
three Ctrl-A bytes to Xen.

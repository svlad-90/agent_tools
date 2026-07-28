# Xen QEMU Harness

Reusable Xen/QEMU runtime harness for Zephyr and zephyr-xenlib tests. It runs a
QEMU command directly or through Docker, streams stdout and stderr into one
domain-prefixed log file, and checks markers while the process is still
running.

## Quick Start

For the workspace Zephyr/Xen validation product, use the preset:

```sh
python -m codex_tools.xen_harness.xen_qemu_harness \
  --preset zephyr-xen-qemu \
  --timeout-sec 10 \
  --log-file zephyr-hypercalls/report/xen-wdt.log \
  --dom0-bin zephyr-xenstore-client/dev/qemu-xen-zephyr-dom0-validation/zephyr_dom0/build-xenstore-srv-runtime-harness3/zephyr/zephyr.bin \
  --domu-bin zephyr-hypercalls/dev/zephyr-xen-hypercalls/build-pr136-xen-wdt-fail-ch0/zephyr/zephyr.bin \
  --expect domu1:'xen-wdt: fail channel 0' \
  --expect xen:'Watchdog timer fired for domain 1'
```

The preset supplies the Docker image, mounts, workdir, QEMU binary path, command
line, and these defaults:

```text
XEN_STATIC_DOMU=0
XEN_LOAD_DOMU_IMAGE=1
DOMU_LOAD_ADDR=0x59000000
```

`0x59000000` is inside the current Dom0 RAM bank. Keep
`-DXEN_HARNESS_DOMU_IMAGE_LOAD_ADDR` in the Dom0 build matched to the same
address.

## Output

`--log-file` is the only harness output. It writes one combined log and does
not create split logs or `summary.json`.

Each line is prefixed with the inferred source:

```text
[xen] (XEN) ...
[dom0] [xen-harness][dom0] ...
[domu1] [xen-harness][domu1] ...
[host] qemu-system-aarch64: ...
```

The harness checks `--expect` and `--require-source` while streaming. Once all
requested markers and sources are present, it terminates the QEMU process group
instead of waiting for `--timeout-sec`. Pass `--no-stop-on-match` when a run
must continue after markers are found.

## Zephyr DomU Console Collection

Static dom0less DomU console switching is not enough for reliable DomU printk
collection in this setup. The reusable path is:

1. Build Zephyr Dom0 with `zephyr-xenlib` and this workspace module.
2. Enable `CONFIG_XEN_HARNESS_DOMU_AUTOSTART=y` and
   `CONFIG_XEN_HARNESS_DOMU_CONSOLE_COLLECTOR=y`.
3. Let Zephyr Dom0 create DomU through `domain_create()`.
4. Let the module attach xenlib's PV console feed and print lines with
   `[xen-harness][domu<N>]`.

The standard config is:

```sh
-DEXTRA_ZEPHYR_MODULES="/workspace/zephyr-xenlib-builders/dev/zephyr-xenlib;/workspace/codex_tools/xen_harness/zephyr_module"
-DOVERLAY_CONFIG=/workspace/codex_tools/xen_harness/zephyr_module/configs/dom0-console-collector.conf
-DXEN_HARNESS_DOMU_IMAGE_LOAD_ADDR=0x59000000
-DXEN_HARNESS_DOMU_IMAGE_SIZE=<domu-zephyr.bin-size>
```

`CONFIG_XEN_LIBFDT=y` is required for zephyr-xenlib DomU creation because the
guest needs a generated device tree.

## ABI Rule

Before debugging any Xen/Zephyr runtime behavior that uses Dom0 control calls,
check `codex_tools/rules/xen-zephyr-abi.md`. A Dom0 `domctl` or `sysctl` ABI
mismatch can fail before policy, domain creation, console setup, or image
loading is reached.

## Generic Mode

For other Xen/QEMU products, pass the command explicitly:

```sh
python -m codex_tools.xen_harness.xen_qemu_harness \
  --log-file task/report/runtime.log \
  --timeout-sec 10 \
  --cmd './run-qemu.sh' \
  --expect xen:'Booting domain'
```

Use `--docker-image`, `--mount`, `--docker-workdir`, and `--env KEY=VALUE` only
when the command needs Docker.

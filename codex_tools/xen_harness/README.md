# Xen QEMU Harness

Reusable Xen/QEMU runtime harness for Zephyr and zephyr-xenlib tests. It runs a
QEMU command through a task-owned scenario, streams stdout and stderr into one
domain-prefixed log file, and checks markers while the process is still
running. Workspace runtime validations should consume target artifacts built by
a task-owned Moulin product and run QEMU/Xen inside the matching Docker-backed
environment.

## Quick Start

For a workspace Zephyr/Xen validation product, build the target artifacts with
the task-owned Moulin product under `task/dev/`, then keep the launch scenario
in the task directory and pass it to the harness:

```sh
codex_tools/xen_harness/scripts/run-scenario.sh \
  task/scripts/xen-harness-scenarios/scenario-name.json
```

The scenario file describes task-specific paths to Moulin-built artifacts, the
Docker environment used to run QEMU/Xen, selected target domains, expected
markers, preflight ABI values, and runtime environment variables. The harness
does not keep a built-in registry of task scenarios.
See `codex_tools/xen_harness/SCENARIO_SCHEMA.md` for the recommended scenario
contract.

Scenario files may use the `zephyr-xen-qemu` preset. The preset supplies the
Docker image, mounts, workdir, QEMU binary path, command line, and these
defaults:

```text
XEN_STATIC_DOMU=0
XEN_LOAD_DOMU_IMAGE=1
DOMU_LOAD_ADDR=0x59000000
```

`0x59000000` is inside the current Dom0 RAM bank. Keep
`-DXEN_HARNESS_DOMU_IMAGE_LOAD_ADDR` in the Dom0 build matched to the same
address.

## Preflight

Before QEMU starts, a scenario file can make the harness check:

- the Dom0 and DomU `zephyr.bin` paths exist;
- the DomU image size matches `XEN_HARNESS_DOMU_IMAGE_SIZE` in the Dom0
  `CMakeCache.txt`;
- the DomU load address matches `XEN_HARNESS_DOMU_IMAGE_LOAD_ADDR`;
- the Dom0 control ABI matches the Xen runtime selected by the task scenario.

For the current Xen 4.19 validation product, the expected ABI is:

```text
CONFIG_XEN_DOMCTL_INTERFACE_VERSION=0x17
CONFIG_XEN_SYSCTL_INTERFACE_VERSION=0x15
```

If any configured preflight check fails, the harness exits before starting
QEMU. That is intentional: ABI or image-size mismatches make runtime failures
misleading.

## Output

`--log-file` writes the combined harness log. By default QEMU stdout/stderr is
the only input stream. For products that can route consoles to separate QEMU
chardev files, pass `--follow-log SOURCE:PATH` for each sidecar log. The
harness tails those files while QEMU is still running, prefixes each line with
the configured source, and applies `--expect SOURCE:...` live instead of
waiting for post-run analysis.

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

Example for a QEMU primary serial routed to a file:

```sh
QEMU_CONSOLE_BACKEND=file \
QEMU_CONSOLE_LOG=report/runtime/qemu-primary.log \
python -m codex_tools.xen_harness.xen_qemu_harness \
  --cmd './run/run-qemu.sh' \
  --timeout-sec 60 \
  --follow-log xen:report/runtime/qemu-primary.log \
  --expect xen:'PR103 REVIEW PROBE PASS' \
  --log-file report/runtime/harness-combined.log
```

For interactive console tests, prefer a QEMU Unix socket chardev when the
product supports it. The harness connects to the socket, reads it as a named
source, and sends timed input to the same bidirectional endpoint:

```sh
QEMU_CONSOLE_BACKEND=socket \
QEMU_CONSOLE_SOCKET=report/runtime/qemu-primary.sock \
python -m codex_tools.xen_harness.xen_qemu_harness \
  --cmd './run/run-qemu.sh' \
  --timeout-sec 60 \
  --console-socket primary:report/runtime/qemu-primary.sock \
  --send-xen-switch-at 4 \
  --expect primary:'PR103 REVIEW PROBE PASS' \
  --log-file report/runtime/harness-combined.log
```

## Scripted Input

The harness can send timed input to QEMU stdin. This is useful for switching
the Xen console to Dom0 and running shell diagnostics while a guest test is
still running.

```sh
python -m codex_tools.xen_harness.xen_qemu_harness \
  --cmd './run/run-qemu.sh' \
  --timeout-sec 60 \
  --send-xen-switch-at 9 \
  --send-line-at '11:root' \
  --send-line-at '13:systemctl status xenstore-init-dom0less.service --no-pager' \
  --send-line-at '15:xenstore-ls -fp /local/domain/1/device || true' \
  --log-file task/report/runtime/dom0-diag.log
```

`--send-at TIME:TEXT` sends decoded text exactly as provided.
`--send-line-at TIME:TEXT` appends a newline. Both decode common escape
sequences such as `\n` and `\x01`. `--send-xen-switch-at TIME` sends the Xen
console-switch control sequence. The older `--xen-switch-at TIME` option is
kept as a compatibility alias.

## Product Integrations

The reusable console contract is:

```text
[xen-harness][domu<N>] guest log line
```

The Python harness maps those records to source `domu<N>` while streaming the
combined log. This keeps Linux Dom0, Zephyr Dom0, and arbitrary DomU guests on
one test-facing convention: guests write to their Xen PV console, and the Dom0
side collector exports the per-domain records.

### Linux Dom0

Use the reusable Yocto layer at
`codex_tools/xen_harness/linux_yocto_layer/meta-xen-harness`. Add the layer to
the product `bblayers.conf`, then add:

```bitbake
IMAGE_INSTALL:append = " xen-harness-console"
```

The package installs `xen-harness-console.service`, which runs after
`xenconsoled` and emits framed harness records. In `auto` mode it starts both
the standard `xenconsole <domid>` collector for toolstack-created PV consoles
and an `xl dmesg` collector for dom0less ARM guests whose VPL011 output appears
as `(XEN) DOM<N>:` hypervisor-log records. Configure domain IDs and backend
selection through `/etc/default/xen-harness-console`. For deterministic shell
proofs, run the installed script with `XEN_HARNESS_CONSOLE_BACKEND=xen-dmesg`
and `XEN_HARNESS_CONSOLE_ONESHOT=1` to dump the current Xen ring once and
return to the shell.

### Zephyr Dom0

Use `codex_tools/xen_harness/zephyr_module` as a Zephyr extra module and enable:

```text
CONFIG_XEN_HARNESS=y
CONFIG_XEN_HARNESS_DOMU_CONSOLE_COLLECTOR=y
```

The Zephyr collector reads DomU Xen PV console rings through zephyr-xenlib. Its
default sink prints the same framed records to Dom0 printk. Products with a
separate host-visible transport can install another sink with
`xen_harness_log_collector_set_sink()` before the collector starts. For that
case disable `CONFIG_XEN_HARNESS_DOMU_CONSOLE_COLLECTOR_AUTOSTART`, install
the sink from product initialization code, then call
`xen_harness_log_collector_start()`.

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

For other Xen/QEMU products or explicitly scoped one-off experiments, pass the
command explicitly:

```sh
python -m codex_tools.xen_harness.xen_qemu_harness \
  --log-file task/report/runtime.log \
  --timeout-sec 10 \
  --cmd './run-qemu.sh' \
  --expect xen:'Booting domain'
```

Use `--docker-image`, `--mount`, `--docker-workdir`, and `--env KEY=VALUE` to
run that command in the same Docker image that owns the runtime product. Record
one-off direct artifact paths in the task `TASK_CONTEXT.md` so later validation
does not accidentally depend on stale host outputs.

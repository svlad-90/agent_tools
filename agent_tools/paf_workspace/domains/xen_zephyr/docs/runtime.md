# Xen/Zephyr Runtime Tasks

The Xen/Zephyr domain owns runtime launch and log collection through PAF task
classes. There is no separate bash runner and no standalone JSON scenario
contract for repeatable validation.

Runtime data is declared in domain YAML under `xen_zephyr.harness`. The PAF
scenario then runs these phases:

```text
harness_scenario
harness_prepare
harness_run
validate
```

Implementation lives under the domain's PAF entry point and support library:

```text
tasks/          PAF task package and phase entry points
lib/runtime.py  runtime parsing, preflight, QEMU process, log streaming
```

Support assets used by runtime products live beside the tasks:

```text
assets/zephyr_module/       Zephyr Dom0 console collector module
assets/linux_yocto_layer/   Linux console collector layer
```

The names `xen_harness_*` that appear inside C symbols, Kconfig options, and
Yocto package files are runtime API names, not workspace entry points.

Replayable evidence is the normal PAF log. PAF prints task exports and
command after parameter substitution for commands executed through its
subprocess and Docker helpers. The runtime task prints the concrete expanded
QEMU or `docker run ... bash -lc ...` command before starting the Python log
collector.

## Console Collection Caveats

The Xen/Zephyr runtime collector stores a combined log and also classifies
lines into source buckets such as `xen`, `dom0`, and `domu1`. Those buckets are
useful for validation and navigation, but they are not a byte-accurate proof of
which domain produced every fragment of a physical console line.

QEMU and Xen console output can be split across reads, interleaved with another
domain, or prefixed by Linux Dom0 terminal text. For example, a Zephyr DomU
test marker can appear after a Dom0 login prompt on the same physical line.
In that case a source-specific `domu1` validation can miss the marker even
though the marker is present in the saved runtime log and visible through the
combined stream.

Before concluding that Linux or Zephyr stopped printing:

- inspect the saved `RUNTIME_LOG_FILE`, not only the terminal transcript;
- search the marker in both its expected source bucket and the combined log;
- treat explicit Xen `DOM<N>:` prefixes and in-guest test markers as stronger
  evidence than the collector's best-effort source label;
- use a `combined` validation expectation for markers that can legitimately
  share a line with Dom0 prompt or systemd output.

An early message such as `xenconsole dom1: Could not read tty from store` can
occur before XenStore or dom0less initialization has published the console path.
By itself it does not prove that the DomU console is dead.

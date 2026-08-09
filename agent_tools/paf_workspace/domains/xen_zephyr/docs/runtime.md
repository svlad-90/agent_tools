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

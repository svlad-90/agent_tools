# Xen/Zephyr Runtime YAML

Runtime launch descriptions live in the domain YAML under
`xen_zephyr.harness`. They are part of the Xen/Zephyr PAF domain contract, not
a separate JSON scenario format and not a shell wrapper contract.

Minimal shape:

```yaml
xen_zephyr:
  harness:
    name: task-runtime
    preset: zephyr-xen-qemu
    log_file: task/report/runtime/harness.log
    timeout_sec: 90
    dom0_bin: task/dev/product/dom0/zephyr.bin
    domu_bin: task/dev/product/domu/zephyr.bin
    expect:
      - source: domu1
        text: PASS
    require_source:
      - xen
      - dom0
      - domu1
```

The PAF scenario splits this into explicit phases:

```text
harness_scenario  -> parse and validate xen_zephyr.harness
harness_prepare   -> optional Zephyr build plus image/ABI preflight
harness_run       -> run QEMU/Xen and evaluate live markers
validate          -> inspect the produced runtime log
```

Use `schema.yaml` as the authoritative field list.

# Xen Harness Scenario Schema

Task-owned scenario files are the stable launch contract between a task's
Moulin-built runtime product and `codex_tools/xen_harness`.

Keep scenario files under the task directory, usually:

```text
task/scripts/xen-harness-scenarios/<name>.json
```

## Required Intent

Every scenario should identify:

- the reusable Docker-backed environment used to run QEMU/Xen;
- the Moulin product or artifact manifest it consumes;
- the Xen image, QEMU binary, Dom0 image, and target DomU images;
- the domain role for each target domain;
- expected log markers and required log sources;
- preflight checks that make stale or incompatible artifacts fail before QEMU
  starts.

## Common Fields

Use these names unless an existing harness implementation requires a more
specific field:

```json
{
  "name": "scenario-name",
  "environment": "codex_tools/environments/zephyr-xen",
  "artifact_manifest": "dev/product-artifacts.yaml",
  "preset": "zephyr-xen-qemu",
  "docker": {
    "image": "image-name",
    "workdir": "/workspace/task/dev/product",
    "mounts": [
      {"source": ".", "target": "/workspace"}
    ],
    "env": {
      "KEY": "VALUE"
    }
  },
  "artifacts": {
    "xen": "path/to/xen",
    "qemu": "path/to/qemu-system-aarch64",
    "dom0": "path/to/dom0/zephyr.bin",
    "domus": [
      {
        "name": "domu1",
        "role": "tested-client",
        "image": "path/to/domu/zephyr.bin"
      }
    ]
  },
  "preflight": {
    "dom0_cmake_cache": "path/to/dom0/CMakeCache.txt",
    "domu_image_size": true,
    "domu_load_address": "0x59000000",
    "xen_domctl_interface_version": "0x17",
    "xen_sysctl_interface_version": "0x15"
  },
  "expect": [
    {"source": "xen", "text": "Booting domain"},
    {"source": "domu1", "text": "PASS"}
  ],
  "require_source": ["xen", "dom0", "domu1"],
  "timeout_sec": 30,
  "log_file": "report/runtime/scenario-name.log"
}
```

## Rules

- Prefer paths that are reproducible from the task directory or workspace root.
- Do not point at manual host build outputs when the Moulin product can produce
  the same artifact.
- Keep domain roles explicit: examples are `control`, `hardware`,
  `xenstore-server`, `console-collector`, `backend-provider`, and
  `tested-client`.
- If a direct one-off artifact path is used, record the exception in
  `TASK_CONTEXT.md`.

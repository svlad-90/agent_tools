# Xen/Zephyr PAF Domain

This domain collects reusable PAF automation for Xen, Zephyr, zephyr-xenlib,
Moulin products, QEMU runs, Dom0/DomU topologies, XenStore, PV devices, and
runtime validation.

The expected layering is:

```text
PAF scenario
  -> check or build a reusable Docker environment
  -> build a Moulin product or selected target artifacts
  -> write an artifact manifest
  -> run codex_tools/xen_harness
  -> collect logs and reports
```

Keep the Xen/QEMU runtime details in `codex_tools/xen_harness` JSON or task
scripts. Keep target selection, environment selection, artifact production, and
multi-phase orchestration in PAF.

Typical parameters that should stay overrideable:

```text
XEN_VERSION
XEN_REF
ZEPHYR_REF
ZEPHYR_XENLIB_REF
PRODUCT_DIR
PRODUCT_BUILD_CMD
SCENARIO_FILE
HARNESS_CMD
ARTIFACT_MANIFEST
```

Use task-local PAF XML while a case is still experimental. Promote it into
`scenarios/` or `templates/` when it becomes a reusable proof pattern.

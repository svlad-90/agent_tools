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

## YAML Domain Metadata

This domain also declares `domain.yaml` and `schema.yaml`. PAF discovers them
through the normal `--import-module-dir codex_tools/paf_workspace` path.

The schema is a JSON Schema document written in YAML syntax. A case can request
this domain with either:

```yaml
case:
  name: pr103-xenstore-client
  domain: xen-zephyr
```

or as one block in a larger automation recipe:

```yaml
uses:
  - domain: xen-zephyr
```

When such a YAML case is passed with `--yaml-config`, PAF validates it, writes
the expanded structured config to `YAML_CONF_FILE`, and projects scalar values
into replayable `YAML_CONF_*` environment variables.

## Generic Build/Run Harness Scenario

`scenarios/build-run-harness.xml` provides the standard Xen/Zephyr
build-and-run shape:

```text
prepare -> build -> run
```

It defines these scenarios:

- `default`: check/build environment, build product artifacts, write an
  artifact manifest, and run the harness.
- `build-only`: check/build environment, build product artifacts, and write an
  artifact manifest.
- `run-only`: check/build environment and run the harness against existing
  artifacts.
- `check-only`: validate workspace/product paths without building or running.

Pass task-specific values through a second PAF XML config:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/xen-zephyr/scenarios/build-run-harness.xml \
  default \
  --config zephyr-xenstore-client/scripts/paf/pr103-xenstore-client-validation.xml
```

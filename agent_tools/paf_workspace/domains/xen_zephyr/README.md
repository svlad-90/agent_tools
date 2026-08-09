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
  -> run Xen/QEMU through domain PAF runtime tasks
  -> collect logs and reports
```

Keep Xen/QEMU runtime details in `xen_zephyr.harness` inside the domain YAML.
Do not add a separate shell or JSON launch contract for repeatable validation.
Target selection, environment selection, artifact production, runtime launch,
and marker validation are domain PAF tasks and phases.

The importable PAF task namespace for this domain is
`paf_workspace.domains.xen_zephyr.tasks`. The public domain name remains
`xen-zephyr` in YAML metadata and profiles.

Typical parameters that should stay overrideable:

```text
XEN_VERSION
XEN_REF
ZEPHYR_REF
ZEPHYR_XENLIB_REF
PRODUCT_DIR
PRODUCT_BUILD_CMD
RUNTIME_LOG_FILE
ARTIFACT_MANIFEST
```

Use task-local PAF XML while a case is still experimental. Promote it into
`scenarios/` or `templates/` when it becomes a reusable proof pattern.

Use `profiles/` for runnable reusable presets, such as `check-only.yaml`.
Use `templates/` for files a task can copy and specialize before it has a
stable reusable scenario. The templates are intentionally not treated as
authoritative validations until the task fills in real product, artifact,
harness scenario, and marker values.

## YAML Domain Metadata

This domain also declares `domain.yaml` and `schema.yaml`. PAF discovers them
through the normal `--import-module-dir agent_tools/paf_workspace` path.

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

The `environments` domain descriptor declares the default Docker image and
container aliases used by this domain:

```yaml
uses:
  - domain: environments

requires:
  images:
    zephyr-xen:
      image: codex/zephyr-xen:latest
      dockerfile: agent_tools/paf_workspace/domains/environments/assets/zephyr-xen/Dockerfile
      context: agent_tools/paf_workspace/domains/environments/assets/zephyr-xen
  containers:
    zephyr-xen-workspace:
      image: zephyr-xen
      workdir: /home/builder/workspace
```

PAF merges those aliases into `docker.images` and `docker.containers` as
defaults. A case file can override them in its own `docker` section, or a run
can override the environment domain descriptor directly:

```sh
--domain-yaml-parameter environments.requires.images.zephyr-xen.image=my/zephyr-xen:debug
```

The domain schema intentionally does not define `docker.images` or
`docker.containers`; PAF validates those built-in sections before applying the
domain-specific `xen-zephyr` schema.

## Generic Build/Run Harness Scenario

`scenarios/build-run-harness.xml` provides the standard Xen/Zephyr
build-and-run shape:

```text
prepare -> build -> harness_scenario -> harness_prepare -> harness_run -> validate
```

It defines these scenarios:

- `default`: check/build the Zephyr/Xen environment, build product artifacts, write an
  artifact manifest, run the domain runtime tasks, and validate runtime
  markers from the YAML profile.
- `build-only`: check/build the Zephyr/Xen environment, build product artifacts, and write an
  artifact manifest.
- `run-only`: check/build the Zephyr/Xen environment, run the domain runtime
  tasks against existing artifacts, and validate runtime markers from the YAML
  profile.
- `check-only`: validate workspace/product paths without building or running.

Set `RUNTIME_LOG_FILE` in the task-local XML when using `default` or
`run-only`. The `validate_runtime_log` task reads `validation.expected` and
`validation.forbidden` from the YAML case profile and checks them against that
log file after the harness returns.

Minimal domain smoke:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/xen_zephyr/scenarios/build-run-harness.xml \
  check-only \
  --yaml-config agent_tools/paf_workspace/domains/xen_zephyr/profiles/check-only.yaml \
  --parameter PRODUCT_DIR=.
```

Pass task-specific values through a second PAF XML config, through a YAML
profile, or through command-line overrides:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/xen_zephyr/scenarios/build-run-harness.xml \
  default \
  --config zephyr-xenstore-client/scripts/paf/pr103-xenstore-client-validation.xml \
  --yaml-config zephyr-xenstore-client/scripts/paf/pr103-xenstore-client-validation.yaml
```

Runtime execution is implemented by domain task classes in `tasks/`. Repeatable
evidence should flow through the normal PAF log so the environment selection,
product build, artifact manifest, runtime settings, logs, and overrides are
captured in one place. PAF already prints task exports and command after
parameter substitution for commands executed through its subprocess and Docker
helpers. The runtime phase also prints the concrete expanded QEMU or
`docker run ...` command before handing it to the Python log collector.

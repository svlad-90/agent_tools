# PAF Workspace Orchestration

PAF is the preferred orchestration layer for complex workspace automation flows
that need to build or fetch several inputs before running a scenario.
Use the public repository as the source of the framework:

```text
https://github.com/svlad-90/paf
```

Do not vendor a copy of PAF into `codex_tools` by default. Keep `codex_tools`
focused on workspace adapters, stable command entry points, reusable
environments, and domain-specific helpers. Vendor PAF only if the workspace
needs a pinned, locally patched version that cannot be consumed as an external
dependency.

`codex_tools/paf_workspace/run-paf.sh` is the workspace entry point. It
uses `PAF_ROOT` when set. If PAF is not present, it clones `PAF_URL` into
`codex_tools/.cache/paf` at `PAF_REF`, and then runs the requested PAF
scenario. Existing PAF checkouts are not updated unless `PAF_UPDATE=1` is set.

Reusable PAF work belongs under `codex_tools/paf_workspace/domains/`. Treat
those directories as automation spheres, similar to
`/home/vladyslav_goncharuk/Projects/tools/aasig_dev_platform/build/`: each
domain collects its own PAF scenarios, profiles, templates, and optional task
modules for typical work. Examples are Xen/Zephyr validation, Moulin product
builds, CI wrappers, report publishing, image manipulation, or hardware lab
flows.

## Boundary

PAF owns high-level orchestration:

- building or checking Docker images;
- building Moulin products;
- resolving target artifacts;
- running ordered validation phases;
- applying retry or return-code policy;
- publishing logs and reports.

Workspace tools own domain-specific execution:

- Xen/Zephyr domain PAF runtime tasks run Xen/QEMU and stream tagged logs;
- `codex_tools/environments/*` builds and runs reusable Docker environments;
- task-local Moulin products produce Xen, Linux, Zephyr, initramfs, DTB, and
  helper artifacts;
- task-local scenario files describe concrete runtime topology and expected
  markers.

GitHub Actions and `act` should call PAF as a wrapper entry point. They should
not become the primary model for Xen/QEMU/Moulin scenario orchestration.

## Recommended Flow

For a repeatable Xen/Zephyr validation case, structure the flow as:

```text
PAF scenario
  -> ensure Docker environment exists
  -> build Moulin product
  -> verify artifact manifest
  -> run Xen/Zephyr domain runtime phases
  -> check runtime markers
  -> collect report artifacts
```

Keep experimental PAF scenarios in the task or product repository that owns the
runtime topology. When a scenario shape becomes reusable, promote the generic
version into `codex_tools/paf_workspace/domains/<domain>/` and keep only
task-specific overrides in the task.

Example:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/xen-zephyr/scenarios/build-run-harness.xml \
  default \
  --config zephyr-xenstore-client/scripts/paf/pr103-xenstore-client-validation.xml
```

Run another scenario from the same config:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/xen-zephyr/scenarios/build-run-harness.xml \
  run-only \
  --config zephyr-xenstore-client/scripts/paf/pr103-xenstore-client-validation.xml
```

Override target-specific parameters without editing the XML:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/xen-zephyr/scenarios/build-run-harness.xml \
  default \
  --config zephyr-xenstore-client/scripts/paf/pr103-xenstore-client-validation.xml \
  --parameter XEN_VERSION=4.21 \
  --parameter ZEPHYR_REF=v4.2.0 \
  --parameter ZEPHYR_XENLIB_REF=codex/pr103-client-local-fixes
```

Structured YAML case files can be layered on top of the XML execution graph:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/xen-zephyr/scenarios/build-run-harness.xml \
  run-only \
  --yaml-config zephyr-xenstore-client/cases/base.yaml \
  --yaml-config zephyr-xenstore-client/cases/pr103-xenstore-client.yaml \
  --yaml-parameter validation.timeout_sec=120
```

PAF discovers optional `domain.yaml` files under imported module directories.
The `xen-zephyr` domain declares a JSON Schema stored as YAML, so case files
that use `case.domain: xen-zephyr` or `uses: [{domain: xen-zephyr}]` are
validated before execution. Validated YAML values are projected into
`YAML_CONF_*` environment variables, and the expanded structured config is
available to tasks through `YAML_CONF_FILE` and `self.get_yaml_config()`.

Domain descriptors can declare required Docker image aliases. PAF merges those
aliases into `docker.images` defaults and lets tasks execute commands through a
container alias:

```yaml
docker:
  containers:
    zephyr-build:
      image: zephyr-xen
      workdir: /workspace
      mounts:
        - source: ${WORKSPACE_ROOT}
          target: /workspace
          mode: rw
```

When a task uses the PAF Docker helpers, PAF expands the container alias to the
actual `docker run ... /bin/bash -lc <command>` invocation and logs it through
the same subprocess command and command-after-substitution output used for
host commands. Use the normal `avoid_printing_command` flags only when the
command text itself is sensitive.

Use `--domain-yaml-parameter` for per-run domain descriptor overrides, for
example:

```sh
--domain-yaml-parameter xen-zephyr.requires.images.zephyr-xen.image=my/zephyr-xen:debug
```

Use `PAF_REF=<branch-or-tag>` to select the PAF revision. Existing cached PAF
checkouts are reused; set `PAF_UPDATE=1` when the wrapper must fetch and
checkout `PAF_REF` again.

The Xen/Zephyr domain describes runtime launches in YAML under
`xen_zephyr.harness`. Repeatable domain validation should flow through PAF
task phases instead of legacy shell or sidecar scenario contracts.

## Data Formats

Prefer existing PAF scenario/config files as the canonical scenario
description. Do not introduce a new workspace format for data that PAF already
models.

If the orchestration needs a build-output contract, use a small artifact
manifest with stable fields such as:

```text
name
path
sha256
producer
created_at
```

The manifest describes produced files only. It should not contain secrets,
host-specific credentials, private service URLs, or mutable local cache paths
unless the task explicitly documents that the file is private and not intended
for publication.

PAF can hide command text and command output through its existing
`avoid_printing_command` and `avoid_printing_command_output` task-call flags.
The workspace generic command tasks expose these as `<COMMAND>_HIDE_COMMAND`
and `<COMMAND>_HIDE_OUTPUT` parameters, for example
`PRODUCT_BUILD_CMD_HIDE_COMMAND=True`.

PAF also masks common sensitive environment parameter names while dumping the
task environment, such as names containing `PASSWORD`, `TOKEN`, `SECRET`,
`PRIVATE_KEY`, `API_KEY`, `ACCESS_KEY`, `PASSPHRASE`, or `CREDENTIAL`. For
scenario-specific names, set `PAF_SECRET_PARAMS` to a space-, comma-, or
semicolon-separated list of exact parameter names. Prefer references to secret
files or environment-provided values over embedding literal secrets in shared
XML files.

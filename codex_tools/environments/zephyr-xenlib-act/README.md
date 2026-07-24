# zephyr-xenlib act environment

This reusable environment runs the `zephyr-xenlib` GitHub Actions `Build`
workflow locally through `act`.

The Dockerfile builds a local `ubuntu-22.04` runner image with the system tools
that the workflow needs before Zephyr SDK setup and build steps can run.

## Commands

Check prerequisites:

```sh
codex_tools/environments/zephyr-xenlib-act/scripts/check.sh
```

Build the runner image:

```sh
codex_tools/environments/zephyr-xenlib-act/scripts/build.sh
```

Run the workflow:

```sh
codex_tools/environments/zephyr-xenlib-act/scripts/validate.sh \
  zephyr-xenlib-builders/dev/zephyr-xenlib
```

The script runs matrix entries as separate `act` invocations by default:
`rcar_spider_ca55`, `rcar_salvator_xs_m3`, `rcar_h3ulcb_ca57`, then
`qemu_cortex_a53`, all with `project=zephyr-dom0-xt`. The workflow writes SDK,
checkout, and build outputs under one workspace path, so one parallel `act`
invocation can race while restoring cache or cleaning checkout directories. Use
`--parallel` only when running isolated workspaces or when the workflow has been
changed to use per-job paths.

Run the matrix in parallel with isolated workspaces:

```sh
codex_tools/environments/zephyr-xenlib-act/scripts/validate.sh \
  zephyr-xenlib-builders/dev/zephyr-xenlib \
  --isolated-parallel
```

This creates per-target workspaces under:

```text
zephyr-xenlib-builders/dev/act-isolated/
```

and writes per-target logs under:

```text
zephyr-xenlib-builders/report/runtime/act-<target>.log
```

The isolated workspaces copy the current `zephyr-xenlib` working tree,
including uncommitted workflow edits, while excluding generated `act`/west
outputs such as `sdk/`, `.west/`, fetched west projects, and `build/`. Each
isolated copy also gets a target-specific generated job id, such as
`build_qemu_cortex_a53`, so independent `act` processes do not collide on
Docker container or volume names.

Run one matrix entry while debugging:

```sh
codex_tools/environments/zephyr-xenlib-act/scripts/validate.sh \
  zephyr-xenlib-builders/dev/zephyr-xenlib \
  --target qemu_cortex_a53 \
  --project zephyr-dom0-xt
```

Pass extra `act` arguments after `--`:

```sh
codex_tools/environments/zephyr-xenlib-act/scripts/validate.sh \
  zephyr-xenlib-builders/dev/zephyr-xenlib \
  -- --verbose
```

## GitHub token

`actions/checkout@v4` requires a non-empty `GITHUB_TOKEN` input. The validation
script reads a token from:

```text
/home/vladyslav_goncharuk/Projects/token
```

Override it with:

```sh
codex_tools/environments/zephyr-xenlib-act/scripts/validate.sh \
  --token-file /path/to/token
```

The script copies the token into a temporary `act` secret file, passes that file
with `--secret-file`, and removes the temporary file when `act` exits.

## Environment

- `ACT_BIN`: path to the `act` binary. Defaults to `act` from `PATH`, then
  `zephyr-xenlib-builders/tools/act`, then `/tmp/act-bin/act`.
- `CODEX_ZEPHYR_XENLIB_ACT_IMAGE`: Docker image tag. Defaults to
  `zephyr-xenlib-act:22.04`.
- `CODEX_DOCKER_BUILD_NETWORK`: network for Docker DNS preflight and image
  build. Defaults to `host`.

`build.sh` runs a small Docker DNS preflight before building and uses
`--network "${CODEX_DOCKER_BUILD_NETWORK}"` for the image build.

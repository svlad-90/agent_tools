# Codex tools act environment

This reusable environment runs Codex tools GitHub Actions workflows locally
through `act`.

The Docker image contains Python, Git, Docker CLI, and a pinned `act` binary.
The validation script runs that image with access to the host Docker socket and
mounts the workspace at the same absolute path so nested job containers can
read the checked-out files.

## Layout

```text
codex_tools/environments/codex-tools-act/
  Dockerfile
  README.md
  scripts/
    check.sh
    build.sh
    env.sh
    run.sh
    validate.sh
```

## Commands

Check prerequisites and the local image:

```sh
codex_tools/environments/codex-tools-act/scripts/check.sh
```

Build or update the image:

```sh
codex_tools/environments/codex-tools-act/scripts/build.sh
```

`build.sh` first runs a small Docker DNS preflight, then builds the image with
`--network "${CODEX_DOCKER_BUILD_NETWORK}"`. The default network is `host`,
which normally gives Docker build containers working DNS on local Linux
workstations. Override it when needed:

```sh
CODEX_DOCKER_BUILD_NETWORK=bridge codex_tools/environments/codex-tools-act/scripts/build.sh
```

Open a shell in the act driver image:

```sh
codex_tools/environments/codex-tools-act/scripts/run.sh bash
```

Run the Codex tools diff-report workflow locally:

```sh
codex_tools/environments/codex-tools-act/scripts/validate.sh
```

Additional arguments are forwarded to `act`:

```sh
codex_tools/environments/codex-tools-act/scripts/validate.sh --verbose
```

## Environment Variables

- `CODEX_TOOLS_ACT_IMAGE`: local act driver image tag. Defaults to
  `codex-tools-act:24.04`.
- `CODEX_TOOLS_ACT_RUNNER_IMAGE`: job runner image used by `act` for
  `ubuntu-latest`. Defaults to `ghcr.io/catthehacker/ubuntu:act-latest`.
- `CODEX_TOOLS_ACT_WORKFLOW`: workflow path. Defaults to
  `.github/workflows/diff-report.yml`.
- `CODEX_DOCKER_BUILD_NETWORK`: network mode for Docker DNS preflight and
  build. Defaults to `host`.

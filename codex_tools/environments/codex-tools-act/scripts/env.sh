#!/usr/bin/env bash

CODEX_ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_WORKSPACE_ROOT="$(cd "${CODEX_ENV_DIR}/../../.." && pwd)"

CODEX_TOOLS_ACT_IMAGE="${CODEX_TOOLS_ACT_IMAGE:-codex-tools-act:24.04}"
CODEX_TOOLS_ACT_RUNNER_IMAGE="${CODEX_TOOLS_ACT_RUNNER_IMAGE:-ghcr.io/catthehacker/ubuntu:act-latest}"
CODEX_DOCKER_BUILD_NETWORK="${CODEX_DOCKER_BUILD_NETWORK:-host}"
CODEX_TOOLS_ACT_WORKFLOW="${CODEX_TOOLS_ACT_WORKFLOW:-.github/workflows/diff-report.yml}"

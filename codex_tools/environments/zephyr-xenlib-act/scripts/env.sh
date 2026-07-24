#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CODEX_ENV_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
export CODEX_WORKSPACE_ROOT="$(cd "${CODEX_ENV_DIR}/../../.." && pwd)"
export CODEX_ZEPHYR_XENLIB_ACT_IMAGE="${CODEX_ZEPHYR_XENLIB_ACT_IMAGE:-zephyr-xenlib-act:22.04}"
export CODEX_DOCKER_BUILD_NETWORK="${CODEX_DOCKER_BUILD_NETWORK:-host}"
export CODEX_DEFAULT_ZEPHYR_XENLIB_REPO="${CODEX_DEFAULT_ZEPHYR_XENLIB_REPO:-${CODEX_WORKSPACE_ROOT}/zephyr-xenlib-builders/dev/zephyr-xenlib}"
export CODEX_DEFAULT_ZEPHYR_XENLIB_TOKEN_FILE="${CODEX_DEFAULT_ZEPHYR_XENLIB_TOKEN_FILE:-${HOME}/Projects/token}"

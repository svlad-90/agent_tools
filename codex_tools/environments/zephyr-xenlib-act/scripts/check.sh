#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "${SCRIPT_DIR}/env.sh"

act_bin="${ACT_BIN:-}"
if [ -z "${act_bin}" ]; then
	if command -v act >/dev/null 2>&1; then
		act_bin=act
	elif [ -x "${CODEX_WORKSPACE_ROOT}/zephyr-xenlib-builders/tools/act" ]; then
		act_bin="${CODEX_WORKSPACE_ROOT}/zephyr-xenlib-builders/tools/act"
	elif [ -x /tmp/act-bin/act ]; then
		act_bin=/tmp/act-bin/act
	else
		echo "act is not installed; set ACT_BIN or put act in PATH"
		exit 1
	fi
fi

if ! command -v docker >/dev/null 2>&1; then
	echo "docker is not installed or not on PATH"
	exit 1
fi

if ! docker image inspect "${CODEX_ZEPHYR_XENLIB_ACT_IMAGE}" >/dev/null 2>&1; then
	echo "missing Docker image: ${CODEX_ZEPHYR_XENLIB_ACT_IMAGE}"
	echo "build it with: ${SCRIPT_DIR}/build.sh"
	exit 1
fi

if [ ! -s "${CODEX_DEFAULT_ZEPHYR_XENLIB_TOKEN_FILE}" ]; then
	echo "missing or empty token file: ${CODEX_DEFAULT_ZEPHYR_XENLIB_TOKEN_FILE}"
	exit 1
fi

docker run --rm "${CODEX_ZEPHYR_XENLIB_ACT_IMAGE}" bash -lc '
set -euo pipefail
git --version
cmake --version | head -1
ninja --version
protoc --version
'

"${act_bin}" --version

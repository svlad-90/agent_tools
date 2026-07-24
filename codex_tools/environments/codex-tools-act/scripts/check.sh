#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "${SCRIPT_DIR}/env.sh"

if ! command -v docker >/dev/null 2>&1; then
	echo "docker is not installed or not on PATH"
	exit 1
fi

if [ ! -S /var/run/docker.sock ]; then
	echo "docker socket is missing: /var/run/docker.sock"
	exit 1
fi

if ! docker image inspect "${CODEX_TOOLS_ACT_IMAGE}" >/dev/null 2>&1; then
	echo "missing Docker image: ${CODEX_TOOLS_ACT_IMAGE}"
	echo "build it with: ${SCRIPT_DIR}/build.sh"
	exit 1
fi

docker run --rm "${CODEX_TOOLS_ACT_IMAGE}" bash -lc '
set -euo pipefail
python3 --version
git --version
docker --version
act --version
'

echo "codex-tools act environment is ready"

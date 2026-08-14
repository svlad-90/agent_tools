#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_DIR="$(cd -- "${TASK_DIR}/../.." && pwd)"
REPO_DIR="/work/tasks/livelooping/dev/LoopRigger"

IMAGE_TAG="${LIVELOOPING_JUCE_IMAGE:-looprigger-juce-linux:24.04}"

if [ "$#" -eq 0 ]; then
    set -- bash
fi

docker run --rm \
    --volume "${WORKSPACE_DIR}:/work" \
    --workdir "${REPO_DIR}" \
    "${IMAGE_TAG}" \
    "$@"

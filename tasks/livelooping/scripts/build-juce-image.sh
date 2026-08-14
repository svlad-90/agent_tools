#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

IMAGE_TAG="${LIVELOOPING_JUCE_IMAGE:-looprigger-juce-linux:24.04}"
DOCKER_NETWORK="${LIVELOOPING_DOCKER_NETWORK:-host}"

docker build \
    --network "${DOCKER_NETWORK}" \
    --tag "${IMAGE_TAG}" \
    --file "${TASK_DIR}/Dockerfile/juce-linux/Dockerfile" \
    "${TASK_DIR}/Dockerfile/juce-linux"

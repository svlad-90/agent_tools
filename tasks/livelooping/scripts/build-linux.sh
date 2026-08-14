#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-base}"

case "${MODE}" in
    base)
        BUILD_DIR="build-linux"
        CONFIG_FLAGS=(
            -G Ninja
            -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
        )
        ;;
    juce-app)
        BUILD_DIR="build-linux-juce"
        CONFIG_FLAGS=(
            -G Ninja
            -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
            -DLIVELOOPING_BUILD_JUCE_APP=ON
        )
        ;;
    plugin-host)
        BUILD_DIR="build-linux-plugin-host"
        CONFIG_FLAGS=(
            -G Ninja
            -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
            -DLIVELOOPING_BUILD_JUCE_PLUGIN_HOST=ON
        )
        ;;
    *)
        echo "usage: $0 [base|juce-app|plugin-host]" >&2
        exit 2
        ;;
esac

"${SCRIPT_DIR}/run-in-juce-env.sh" bash -lc "
    set -euo pipefail
    cmake -S . -B '${BUILD_DIR}' ${CONFIG_FLAGS[*]@Q}
    cmake --build '${BUILD_DIR}'
    ctest --test-dir '${BUILD_DIR}' --output-on-failure
"

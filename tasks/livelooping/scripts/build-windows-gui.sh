#!/usr/bin/env bash
set -euo pipefail

WINDOWS_SSH_TARGET="${LIVELOOPING_WINDOWS_SSH_TARGET:-svlad@192.168.150.1}"
WINDOWS_SSH_KEY="${LIVELOOPING_WINDOWS_SSH_KEY:-${HOME}/.ssh/id_rsa}"
WINDOWS_REPO_DIR="${LIVELOOPING_WINDOWS_REPO_DIR:-C:\\Users\\svlad\\dev\\LoopRigger}"
VSDEVCMD="${LIVELOOPING_WINDOWS_VSDEVCMD:-C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\Common7\\Tools\\VsDevCmd.bat}"
BUILD_DIR="${LIVELOOPING_WINDOWS_BUILD_DIR:-build-windows-juce}"

REMOTE_COMMAND="call \"${VSDEVCMD}\" -arch=x64 -host_arch=x64 && cd /d \"${WINDOWS_REPO_DIR}\" && cmake -S . -B \"${BUILD_DIR}\" -G Ninja -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DLIVELOOPING_BUILD_JUCE_APP=ON && cmake --build \"${BUILD_DIR}\" && ctest --test-dir \"${BUILD_DIR}\" --output-on-failure"

ssh -i "${WINDOWS_SSH_KEY}" "${WINDOWS_SSH_TARGET}" "${REMOTE_COMMAND}"

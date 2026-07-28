#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

cd "${WORKSPACE_ROOT}"
python -m codex_tools.xen_harness.xen_qemu_harness --scenario-file "$@"

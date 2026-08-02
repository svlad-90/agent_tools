#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

repo_root="${1:-${WORKSPACE_ROOT}/moulin-svlad-90}"
if [ "$#" -gt 0 ]; then
	shift
fi

exec "${WORKSPACE_ROOT}/codex_tools/paf_workspace/run-paf.sh" \
	"${WORKSPACE_ROOT}/codex_tools/paf_workspace/domains/environments/scenarios/moulin-act.xml" \
	validate \
	--yaml-config "${WORKSPACE_ROOT}/codex_tools/paf_workspace/domains/environments/profiles/moulin-act.yaml" \
	--parameter "MOULIN_REPO_ROOT=${repo_root}" \
	"$@"

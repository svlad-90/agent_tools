#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd "${script_dir}/../.." && pwd)"

if [ "$#" -lt 1 ]; then
  echo "usage: $0 CONFIG_XML [SCENARIO] [--parameter KEY=VALUE ...] [--yaml-config CASE.yaml ...]" >&2
  exit 2
fi

paf_url="${PAF_URL:-https://github.com/svlad-90/paf.git}"
paf_ref="${PAF_REF:-main}"
paf_root="${PAF_ROOT:-${workspace_root}/codex_tools/.cache/paf}"
log_dir="${PAF_LOG_DIR:-${workspace_root}/report/paf}"

if [ ! -f "${paf_root}/paf_main.py" ]; then
  mkdir -p "$(dirname "${paf_root}")"
  git clone --branch "${paf_ref}" "${paf_url}" "${paf_root}"
fi

if [ "${PAF_UPDATE:-0}" = "1" ]; then
  git -C "${paf_root}" fetch --tags origin
  git -C "${paf_root}" checkout "${paf_ref}"
fi

mkdir -p "${log_dir}"

export PYTHONPATH="${paf_root}:${PYTHONPATH:-}"

config_path="$1"
scenario_name="${2:-default}"
shift
if [ "$#" -gt 0 ]; then
  shift
fi

python "${paf_root}/paf_main.py" \
  --import-module-dir "${workspace_root}/codex_tools/paf_workspace" \
  --config "${config_path}" \
  --scenario "${scenario_name}" \
  --log-dir "${log_dir}" \
  --parameter "WORKSPACE_ROOT=${workspace_root}" \
  --parameter "PAF_ROOT=${paf_root}" \
  "$@"

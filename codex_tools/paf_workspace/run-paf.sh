#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd "${script_dir}/../.." && pwd)"

if [ "$#" -lt 1 ]; then
  echo "usage: $0 CONFIG_XML [SCENARIO] [PAF_ARGS ...]" >&2
  echo "example:" >&2
  echo "  $0 codex_tools/paf_workspace/domains/<domain>/scenarios/<scenario>.xml default \\" >&2
  echo "    --yaml-config path/to/profile.yaml \\" >&2
  echo "    --parameter KEY=VALUE" >&2
  exit 2
fi

paf_url="${PAF_URL:-https://github.com/svlad-90/paf.git}"
paf_ref="${PAF_REF:-35d66a21b587c8621d822e66b428a7dc080ea962}"
paf_root="${PAF_ROOT:-${workspace_root}/codex_tools/.cache/paf}"
log_dir="${PAF_LOG_DIR:-${workspace_root}/report/paf}"

if [ ! -f "${paf_root}/paf_main.py" ]; then
  mkdir -p "$(dirname "${paf_root}")"
  git clone "${paf_url}" "${paf_root}"
fi

if [ "${PAF_UPDATE:-0}" = "1" ] ||
   ! git -C "${paf_root}" rev-parse --verify "${paf_ref}^{commit}" >/dev/null 2>&1; then
  git -C "${paf_root}" fetch --tags origin
fi

git -C "${paf_root}" checkout "${paf_ref}"

mkdir -p "${log_dir}"

export PYTHONPATH="${paf_root}:${workspace_root}/codex_tools:${PYTHONPATH:-}"

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

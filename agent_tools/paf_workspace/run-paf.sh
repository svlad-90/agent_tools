#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace_root="$(cd "${script_dir}/../.." && pwd)"

if [ "$#" -lt 1 ]; then
  echo "usage: $0 CONFIG_XML [SCENARIO] [PAF_ARGS ...]" >&2
  echo "example:" >&2
  echo "  $0 agent_tools/paf_workspace/domains/<domain>/scenarios/<scenario>.xml default \\" >&2
  echo "    --yaml-config path/to/profile.yaml \\" >&2
  echo "    --parameter KEY=VALUE" >&2
  exit 2
fi

paf_url="${PAF_URL:-https://github.com/svlad-90/paf.git}"
paf_ref="${PAF_REF:-d65ca0fb33be9add41c65a194a6c307c2e24656c}"
paf_root="${PAF_ROOT:-${workspace_root}/agent_tools/.cache/paf}"
paf_venv="${PAF_VENV:-${workspace_root}/agent_tools/.cache/paf-venv}"
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
git -C "${paf_root}" reset --hard "${paf_ref}" >/dev/null

mkdir -p "${log_dir}"

export PYTHONPATH="${paf_root}:${workspace_root}/agent_tools:${PYTHONPATH:-}"

if command -v python3 >/dev/null 2>&1; then
  python_bin=python3
elif command -v python >/dev/null 2>&1; then
  python_bin=python
else
  echo "error: python3/python was not found in PATH" >&2
  exit 127
fi

if [ ! -x "${paf_venv}/bin/python" ]; then
  "${python_bin}" -m venv "${paf_venv}"
fi

if ! "${paf_venv}/bin/python" - <<'PY'
import importlib.util
import sys

missing = [
    package
    for package, module in (
        ("coloredlogs>=15.0.1", "coloredlogs"),
        ("jsonschema>=4.0.0", "jsonschema"),
        ("paramiko>=3.0.0", "paramiko"),
        ("pytest>=8.0.0", "pytest"),
        ("PyYAML>=5.4.1", "yaml"),
    )
    if importlib.util.find_spec(module) is None
]
sys.exit(1 if missing else 0)
PY
then
  "${paf_venv}/bin/python" -m pip install --upgrade \
    "coloredlogs>=15.0.1" \
    "jsonschema>=4.0.0" \
    "paramiko>=3.0.0" \
    "pytest>=8.0.0" \
    "PyYAML>=5.4.1"
fi

config_path="$1"
scenario_name="${2:-default}"
shift
if [ "$#" -gt 0 ]; then
  shift
fi

"${paf_venv}/bin/python" "${paf_root}/paf_main.py" \
  --import-module-dir "${workspace_root}/agent_tools/paf_workspace" \
  --config "${config_path}" \
  --scenario "${scenario_name}" \
  --log-dir "${log_dir}" \
  --parameter "WORKSPACE_ROOT=${workspace_root}" \
  --parameter "PAF_ROOT=${paf_root}" \
  "$@"

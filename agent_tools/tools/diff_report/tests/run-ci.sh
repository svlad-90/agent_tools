#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"

while IFS= read -r path; do
  python -m agent_tools.tools.code_map parse-check "$path"
done < <(find agent_tools/tools/diff_report -name '*.py' -type f | sort | sed 's#^agent_tools/##')

python -m unittest discover -s agent_tools/tools/diff_report/tests

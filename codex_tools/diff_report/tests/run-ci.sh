#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

while IFS= read -r path; do
  python -m codex_tools.code_map parse-check "$path"
done < <(find codex_tools/diff_report -name '*.py' -type f | sort)

python -m unittest discover -s codex_tools/diff_report/tests

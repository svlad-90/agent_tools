#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

python -m codex_tools.code_map parse-check codex_tools/diff_report/core.py
python -m codex_tools.code_map parse-check codex_tools/diff_report/assets.py
python -m codex_tools.code_map parse-check codex_tools/diff_report/cli.py
python -m codex_tools.code_map parse-check codex_tools/diff_report/comments.py
python -m codex_tools.code_map parse-check codex_tools/diff_report/diff_parse.py
python -m codex_tools.code_map parse-check codex_tools/diff_report/diff_source.py
python -m codex_tools.code_map parse-check codex_tools/diff_report/models.py
python -m codex_tools.code_map parse-check codex_tools/diff_report/refresh.py
python -m codex_tools.code_map parse-check codex_tools/diff_report/render.py
python -m codex_tools.code_map parse-check codex_tools/diff_report/__init__.py
python -m codex_tools.code_map parse-check codex_tools/diff_report/__main__.py
python -m codex_tools.code_map parse-check codex_tools/diff_report/tests/test_diff_report_behavior.py
python -m codex_tools.code_map parse-check codex_tools/diff_report/tests/test_pr139_report_regression.py

python -m unittest discover -s codex_tools/diff_report/tests

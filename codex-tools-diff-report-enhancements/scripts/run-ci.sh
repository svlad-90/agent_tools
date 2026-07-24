#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

python -m codex_tools.code_map parse-check codex_tools/diff_report/core.py
python -m codex_tools.code_map parse-check codex_tools/diff_report/__init__.py
python -m codex_tools.code_map parse-check codex_tools/diff_report/__main__.py
python -m codex_tools.code_map parse-check codex_tools/diff_report/tests/test_pr139_report_regression.py

python -m unittest codex_tools.diff_report.tests.test_pr139_report_regression

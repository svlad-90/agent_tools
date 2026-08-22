#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"

show_error() {
  local message="$1"
  if command -v osascript >/dev/null 2>&1; then
    osascript -e "display alert \"Agent Workspace\" message \"$message\"" >/dev/null 2>&1 || true
  else
    printf '%s\n' "$message" >&2
  fi
}

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=python
else
  show_error "python3/python was not found in PATH."
  exit 127
fi

set +e
"$PYTHON_BIN" -m agent_tools.tools.agent_workspace --ui web "$@"
status=$?
set -e
if [ "$status" -ne 0 ]; then
  show_error "Agent Workspace exited with status $status."
  exit "$status"
fi

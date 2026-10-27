#!/usr/bin/env sh
WORKSPACE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="$WORKSPACE_ROOT${PYTHONPATH:+:$PYTHONPATH}"
ulimit -c unlimited 2>/dev/null || true
exec "$WORKSPACE_ROOT/agent_tools/.venv/bin/python3" -m agent_tools.agent_workspace "$@"

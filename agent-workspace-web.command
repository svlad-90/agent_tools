#!/usr/bin/env sh
WORKSPACE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="$WORKSPACE_ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec "$WORKSPACE_ROOT/agent_tools/.venv/bin/python3" -m agent_tools.agent_workspace --ui web "$@"

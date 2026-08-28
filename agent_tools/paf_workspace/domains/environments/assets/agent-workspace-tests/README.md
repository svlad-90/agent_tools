# Agent Workspace Tests Environment

Docker image source for the Agent Workspace test environment.

The image contains the Python, Tk, GTK, and VTE dependencies required by the
Agent Workspace component test tree under
`agent_tools/agent_workspace/components`. It also includes `xvfb-run` for GTK
tests that must realize widgets and exercise event delivery through a real
display connection.

Build and run the validation through PAF:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/environments/scenarios/agent-workspace-tests.xml \
  validate \
  --yaml-config agent_tools/paf_workspace/domains/environments/profiles/agent-workspace-tests.yaml
```

Check an already built image without rebuilding:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/environments/scenarios/agent-workspace-tests.xml \
  check-only \
  --yaml-config agent_tools/paf_workspace/domains/environments/profiles/agent-workspace-tests.yaml
```

Override the pytest command when needed:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/environments/scenarios/agent-workspace-tests.xml \
  validate \
  --yaml-config agent_tools/paf_workspace/domains/environments/profiles/agent-workspace-tests.yaml \
  --parameter AGENT_WORKSPACE_TEST_COMMAND='set -euo pipefail
export PYTHONPATH=.:agent_tools
export PYTHONUNBUFFERED=1
echo "Agent Workspace component tests: start"
timeout --foreground --signal=INT --kill-after=10s 300s \
  xvfb-run -a python3 -X faulthandler -m pytest -vv --maxfail=1 -ra \
  agent_tools/agent_workspace/components/workspace_service/tests
echo "Agent Workspace component tests: passed"'
```

Avoid `pytest -q` for Agent Workspace and GTK diagnostics. Quiet pytest output
can make an Xvfb or GTK hang look like a silent PAF stall. If the output is too
large, use the `limited_bash` live log paths from the truncation notice and
inspect them with `tail`, `rg`, or `sed -n`.

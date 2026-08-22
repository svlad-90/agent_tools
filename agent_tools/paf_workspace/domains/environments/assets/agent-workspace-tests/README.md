# Agent Workspace Tests Environment

Docker image source for the Agent Workspace test environment.

The image contains the Python, Tk, GTK, and VTE dependencies required by
`agent_tools/tools/agent_workspace/tests/test_agent_workspace_core.py`. The
default validation also runs `test_agent_workspace_headless.py` to guard the
service/web boundary against accidental GTK imports.

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
  --parameter AGENT_WORKSPACE_TEST_COMMAND='PYTHONPATH=.:agent_tools python3 -m pytest -q agent_tools/tools/agent_workspace/tests/test_agent_workspace_headless.py'
```

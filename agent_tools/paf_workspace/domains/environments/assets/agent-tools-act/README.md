# Agent Tools Act Asset

Docker image source for the `agent-tools-act` environment.

Use the PAF domain entry points:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/environments/scenarios/agent-tools-act.xml \
  check-only \
  --yaml-config agent_tools/paf_workspace/domains/environments/profiles/agent-tools-act.yaml
```

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/environments/scenarios/agent-tools-act.xml \
  validate \
  --yaml-config agent_tools/paf_workspace/domains/environments/profiles/agent-tools-act.yaml
```

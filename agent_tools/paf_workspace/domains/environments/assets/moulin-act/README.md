# Moulin Act Asset

Docker image source for the `moulin-act` environment. The image reproduces
`ubuntu-22.04` GitHub Actions jobs for Moulin-related repositories, including
Moulin Remote Client.

PAF runs `act` from the separate `agent-tools-act` driver container, which has
the host Docker socket mounted. The host therefore does not need its own `act`
installation. This image is used only as the `ubuntu-22.04` Actions runner.

Use the PAF domain entry points:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/environments/scenarios/moulin-act.xml \
  check-only \
  --yaml-config agent_tools/paf_workspace/domains/environments/profiles/moulin-act.yaml
```

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/environments/scenarios/moulin-act.xml \
  validate \
  --yaml-config agent_tools/paf_workspace/domains/environments/profiles/moulin-act.yaml \
  --parameter MOULIN_REPO_ROOT=/path/to/moulin
```

The selected workflow must expose a job named `build` on `ubuntu-22.04`.

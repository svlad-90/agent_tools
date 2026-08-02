# Moulin Act Asset

Docker image source for the `moulin-act` environment.

Use the PAF domain entry points:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/environments/scenarios/moulin-act.xml \
  check-only \
  --yaml-config codex_tools/paf_workspace/domains/environments/profiles/moulin-act.yaml
```

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/environments/scenarios/moulin-act.xml \
  validate \
  --yaml-config codex_tools/paf_workspace/domains/environments/profiles/moulin-act.yaml \
  --parameter MOULIN_REPO_ROOT=/path/to/moulin
```

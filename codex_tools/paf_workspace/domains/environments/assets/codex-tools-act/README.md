# Codex Tools Act Asset

Docker image source for the `codex-tools-act` environment.

Use the PAF domain entry points:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/environments/scenarios/codex-tools-act.xml \
  check-only \
  --yaml-config codex_tools/paf_workspace/domains/environments/profiles/codex-tools-act.yaml
```

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/environments/scenarios/codex-tools-act.xml \
  validate \
  --yaml-config codex_tools/paf_workspace/domains/environments/profiles/codex-tools-act.yaml
```

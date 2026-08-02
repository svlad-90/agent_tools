# Zephyr Xenlib Act Asset

Docker image source for the `zephyr-xenlib-act` environment.

Use the PAF domain entry points:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/environments/scenarios/zephyr-xenlib-act.xml \
  check-only \
  --yaml-config codex_tools/paf_workspace/domains/environments/profiles/zephyr-xenlib-act.yaml
```

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/environments/scenarios/zephyr-xenlib-act.xml \
  validate \
  --yaml-config codex_tools/paf_workspace/domains/environments/profiles/zephyr-xenlib-act.yaml \
  --parameter ZEPHYR_XENLIB_REPO_ROOT=/path/to/zephyr-xenlib \
  --parameter ZEPHYR_XENLIB_TOKEN_FILE=/path/to/token
```

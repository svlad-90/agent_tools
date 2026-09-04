# Agent Tools Repo Validation Domain

This domain validates an `agent_tools` repository checkout in the reusable
`agent-workspace-tests` Docker image. It is an orchestration domain: the Docker
image remains owned by `domains/environments`, while this domain defines the
checks that make an Agent Tools repo or task push-ready.

Default `validate` checks:

- `git diff --check`;
- `python3 -m py_compile` for Python files;
- `python3 -m agent_tools.tools.code_map parse-check` for Python files under
  `agent_tools/`;
- `pytest` under `xvfb-run` for the configured repo test targets;
- UI contract smoke under `xvfb-run`, requiring real GTK by default;
- optional `task_check --strict-warnings` when `AGENT_TOOLS_VALIDATE_TASK_DIR`
  is set.

Use `push-guard` when the same validation should stamp the repository for the
workspace push guard:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/agent_tools_repo_validation/scenarios/agent-tools-repo.xml \
  push-guard \
  --yaml-config agent_tools/paf_workspace/domains/agent_tools_repo_validation/profiles/agent-tools-repo.yaml \
  --parameter AGENT_TOOLS_VALIDATE_REPO=. \
  --parameter AGENT_TOOLS_VALIDATE_TASK_DIR=tasks/agent_tools_development \
  --parameter PUSH_GUARD_REPO=. \
  --parameter PUSH_GUARD_SOURCE=agent-tools-repo-validation
```

For a faster loop against only changed Python files, add:

```sh
--parameter AGENT_TOOLS_VALIDATE_SCOPE=changed \
--parameter AGENT_TOOLS_VALIDATE_BASE_REF=origin/main
```

Use `check-only` to verify that the reusable image already exists and has the
required baseline tools without running repo tests.

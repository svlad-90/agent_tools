# Validation Policy

This directory contains declarative validation policy consumed by
`agent_tools.tools.repo_guard`.

`workspace-policy.yaml` defines workspace-wide checks. `repos/*.yaml` adds
checks and identity evidence for specific repositories. Task-local policy may
be added as `tasks/<task>/TASK_GUARD.yaml`.

The current push guard does not call `repo_guard` yet. Wire that integration
only after the policy runner and receipts are proven stable.

# Validation Policy

This directory contains declarative validation policy consumed by
`agent_tools.tools.repo_guard`.

`agent_tools.validation.policy` is the shared Python API for loading and
resolving that policy. It returns a `ResolvedPolicy` with the matched
repository identity, the ordered check list, contributing policy documents, and
a stable hash for receipt validation.

`workspace-policy.yaml` defines workspace-wide checks. `repos/*.yaml` adds
checks and identity evidence for specific repositories. Task-local policy may
be added as `tasks/<task>/TASK_GUARD.yaml`.

Installing push guard hooks enables `repo_guard` for that repository. The
installed pre-push hook then runs `repo_guard` by default. Use
`python3 -m agent_tools.tools.push_guard disable-repo-guard --repo <repo>` only
as a repository-local escape hatch when the policy runner itself is blocking
unrelated work.

Task UI actions install or update hooks only for repositories listed in the
task context `repo-registry` slot. They do not recursively scan `dev/` trees;
agents should add or remove registry entries when they identify the repository
roots used by the task.

Policy is layered in this order:

1. `workspace-policy.yaml` for checks that apply across the workspace.
2. `repos/*.yaml` for repository identity evidence and repository checks.
3. `tasks/<task>/TASK_GUARD.yaml` for task-local checks.

Repository identity is resolved from repository names, GitHub remotes including
forks when allowed, required characteristic files, and an optional
`verify_command`.

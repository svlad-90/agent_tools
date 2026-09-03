# repo_guard

`repo_guard` is the shared validation policy runner for workspace repositories.
It is intentionally separate from `push_guard`: the existing pre-push hook is
not wired to this runner yet.

## Commands

```sh
python3 -m agent_tools.tools.repo_guard policy --repo .
python3 -m agent_tools.tools.repo_guard status --repo .
python3 -m agent_tools.tools.repo_guard validate --repo .
python3 -m agent_tools.tools.repo_guard validate --repo . --include-heavy
python3 -m agent_tools.tools.repo_guard pre-push-dry-run --repo . --remote origin
python3 -m agent_tools.tools.repo_guard pre-push --repo . origin <url>
```

`policy` and `status` print the resolved policy without running checks.
`validate` runs policy checks and writes receipts under the repository Git
metadata. `pre-push-dry-run` builds a pre-push-like commit range from the
current branch and its upstream, then runs the same non-heavy checks and heavy
receipt checks without installing or invoking a Git hook. `pre-push` accepts
normal Git pre-push stdin, runs non-heavy checks, and requires current receipts
for heavy checks.

## Policy

Workspace policy lives under:

```text
agent_tools/validation/workspace-policy.yaml
agent_tools/validation/repos/*.yaml
tasks/<task>/TASK_GUARD.yaml
```

Repository identity is resolved from GitHub URLs, fork-compatible repository
names, characteristic files, and an optional `verify_command`.

Check ids are stable policy identifiers, not exported low-level tools. They
are bound into receipts with the repository, commit range, changed path scope,
policy hash, checker config, backend, and task context.

## Backends

- `builtin` - workspace-owned checks such as commit messages, file hygiene,
  changed Python parse checks, and shell syntax checks.
- `command` - repo-specific command declared in policy.
- `paf` - PAF scenario dispatch.
- `task_check` - workspace task hygiene check.
- `task_command` - task-local script or command.

Only high-level surfaces should be exposed to agents or GUI code:

```text
workspace_validation_policy
workspace_validation_status
workspace_validate
```

Internal checker backends should stay internal to avoid cluttering MCP and
skill lists.

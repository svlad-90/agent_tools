---
name: moulin-local-validation
description: Validate Moulin changes locally with the workspace act environment and the real GitHub Actions workflow. Use when asked to run act, verify Moulin CI locally, check mypy/flake8/pytest/gitlint through the workflow, or reproduce Moulin pull_request build jobs without pushing.
---

# Moulin Local Validation

Use the reusable runner stored in this workspace instead of reconstructing the
`act` command manually. Do not depend on a globally installed Codex skill for
this workflow.

Read `codex_tools/environments/moulin-act/README.md` when environment details,
image rebuilds, or forwarded `act` arguments matter.

## Commands

Default validation from the workspace root:

```sh
codex_tools/environments/moulin-act/scripts/validate.sh moulin-svlad-90
```

For a different Moulin checkout, pass that checkout path as the first argument:

```sh
codex_tools/environments/moulin-act/scripts/validate.sh path/to/moulin
```

After changing the local act Dockerfile, rebuild the runner image first:

```sh
codex_tools/environments/moulin-act/scripts/build.sh
codex_tools/environments/moulin-act/scripts/validate.sh path/to/moulin
```

Additional arguments after `--` are forwarded to `act`:

```sh
codex_tools/environments/moulin-act/scripts/validate.sh path/to/moulin -- --verbose
```

The environment maps the GitHub Actions `ubuntu-22.04` runner to the local
`moulin-act:22.04` image and runs the real `pull_request` `build` job.

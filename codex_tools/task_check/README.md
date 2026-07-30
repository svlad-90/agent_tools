# task_check

Check whether a workspace task directory has enough structure and metadata for
a predictable agent workflow.

## Usage

```sh
python -m codex_tools.task_check task-name
```

Run from the workspace root. The command checks the standard task layout,
`TASK_CONTEXT.md` sections, validation-level tracking, product artifact
manifests, and Xen harness scenario metadata.

Create a missing task layout without overwriting an existing context file:

```sh
python -m codex_tools.task_check task-name --init-layout
```

Create the starter files for a Xen/QEMU/Moulin runtime product:

```sh
python -m codex_tools.task_check task-name --init-runtime-product
```

This also creates the base task layout when needed. It adds
`dev/product-artifacts.yaml`, `scripts/xen-harness-scenarios/scenario-name.json`,
and `report/runtime/` without overwriting existing files.
When a scenario references a `codex_tools/environments/...` directory,
`task_check` verifies that the environment's Dockerfile, README, and standard
scripts are present without running Docker.
It also checks filled artifact paths in the scenario; empty values and obvious
placeholders are reported as not filled yet instead of failures.

Use JSON output when another script should consume the result:

```sh
python -m codex_tools.task_check task-name --json
```

By default warnings do not make the command fail. Use `--strict-warnings` when
the task should be complete before a long build or runtime run:

```sh
python -m codex_tools.task_check task-name --strict-warnings
```

Runtime-product and Xen scenario checks are enabled automatically when
`TASK_CONTEXT.md` contains Xen/QEMU/Moulin hints or matching files already
exist. Force those checks explicitly before setting up a new runtime task:

```sh
python -m codex_tools.task_check task-name --runtime-product --xen-runtime
```

Print the reusable environment preflight command before a long build or runtime
run:

```sh
python -m codex_tools.task_check task-name --env-check-command
```

Run the discovered `scripts/check.sh` commands explicitly:

```sh
python -m codex_tools.task_check task-name --run-env-check
```

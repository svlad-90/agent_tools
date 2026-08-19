# task_check

Check whether a workspace task directory has enough structure and metadata for
a predictable agent workflow.

## Usage

```sh
python -m agent_tools.paf_workspace.task_check task-name
```

Run from the workspace root. The command checks the standard task layout,
`TASK_DESCRIPTION.md`, compact `TASK_CONTEXT.md`, and `TASK_CONTEXT.sqlite3`,
validation-level tracking for legacy context files, product artifact manifests,
and Xen/Zephyr runtime YAML metadata.
The structured context format is mandatory: `TASK_CONTEXT.sqlite3` must exist
and be readable, and `TASK_CONTEXT.md` must be generated from that database.
For a task that still has the legacy `TASK_CONTEXT_LOG.jsonl`, run
`python -m agent_tools.tools.task_context migrate --task tasks/task-name`.

Create a missing task layout without overwriting an existing description or
context file:

```sh
python -m agent_tools.paf_workspace.task_check task-name --init-layout
```

The initialized context file is intentionally compact. Durable task history
belongs in `TASK_CONTEXT.sqlite3` and should be maintained with:

```sh
python -m agent_tools.tools.task_context add --task tasks/task-name ...
python -m agent_tools.tools.task_context compact --task tasks/task-name
```

Create the starter files for a Xen/QEMU/Moulin runtime product:

```sh
python -m agent_tools.paf_workspace.task_check task-name --init-runtime-product
```

This also creates the base task layout when needed. It adds
`dev/product-artifacts.yaml`, `scripts/paf/xen-zephyr-runtime.yaml`, and
`report/runtime/` without overwriting existing files.
When runtime YAML uses the `environments` PAF domain, `task_check` can print or
run the domain's safe check-only PAF scenario.

Use JSON output when another script should consume the result:

```sh
python -m agent_tools.paf_workspace.task_check task-name --json
```

Show only failing checks plus the summary when the full pass list is too noisy:

```sh
python -m agent_tools.paf_workspace.task_check task-name --errors-only
```

By default warnings do not make the command fail. Use `--strict-warnings` when
the task should be complete before a long build or runtime run:

```sh
python -m agent_tools.paf_workspace.task_check task-name --strict-warnings
```

`--strict-warnings` uses `warning-policy.yaml` for intentionally non-critical
warnings. At the moment, auto-detected runtime/product readiness reminders such
as a missing `product-artifacts.yaml` or missing Xen runtime YAML do not make
strict mode fail when they were enabled only by context hints. They do become
strict-fatal when the corresponding check is explicitly requested with
`--runtime-product`, `--xen-runtime`, or `--init-runtime-product`.

Runtime-product and Xen runtime YAML checks are enabled automatically when
`TASK_CONTEXT.md` contains Xen/QEMU/Moulin hints or matching files already
exist. Force those checks explicitly before setting up a new runtime task:

```sh
python -m agent_tools.paf_workspace.task_check task-name --runtime-product --xen-runtime
```

Print the reusable environment preflight command before a long build or runtime
run:

```sh
python -m agent_tools.paf_workspace.task_check task-name --env-check-command
```

Run the PAF environment-domain check command explicitly:

```sh
python -m agent_tools.paf_workspace.task_check task-name --run-env-check
```

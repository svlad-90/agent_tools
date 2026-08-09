# task_check

Check whether a workspace task directory has enough structure and metadata for
a predictable agent workflow.

## Usage

```sh
python -m agent_tools.paf_workspace.task_check task-name
```

Run from the workspace root. The command checks the standard task layout,
`TASK_DESCRIPTION.md`, `TASK_CONTEXT.md` sections, validation-level tracking,
product artifact manifests, and Xen/Zephyr runtime YAML metadata.

Create a missing task layout without overwriting an existing description or
context file:

```sh
python -m agent_tools.paf_workspace.task_check task-name --init-layout
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

By default warnings do not make the command fail. Use `--strict-warnings` when
the task should be complete before a long build or runtime run:

```sh
python -m agent_tools.paf_workspace.task_check task-name --strict-warnings
```

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

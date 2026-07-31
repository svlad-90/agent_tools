# PAF Automation Domains

Each subdirectory is a reusable automation sphere. A domain groups PAF tasks
and XML scenarios by the kind of work being automated, not by one temporary
debug task.

Follow this contract for new domains:

```text
domains/<domain>/
  README.md
  tasks.py              # optional
  scenarios/*.xml       # runnable scenario definitions
  profiles/*.xml        # optional target/environment variants
  templates/*.xml       # optional task-local starting points
```

Scenarios should be runnable through:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/<domain>/scenarios/<scenario>.xml \
  <scenario-name>
```

Use PAF command-line `--parameter KEY=VALUE` overrides for revisions, branches,
target paths, and other per-task values. Do not fork a scenario file only to
change a Zephyr, Xen, `zephyr-xenlib`, or product revision.

# PAF Automation Domains

Each subdirectory is a reusable automation sphere. A domain groups PAF tasks
and XML scenarios by the kind of work being automated, not by one temporary
debug task.

Follow this contract for new domains:

```text
domains/<domain>/
  README.md
  scenarios/*.xml       # runnable scenario definitions
  profiles/*.xml        # optional target/environment variants
  templates/*.xml       # optional task-local starting points
```

Python task modules need importable package names. If a domain name contains
characters that are awkward in Python imports, keep the metadata directory name
as the public domain name and place Python tasks under an importable namespace
beside `domains/`. For example, the `xen-zephyr` domain uses:

```text
paf_workspace/xen_zephyr/tasks.py
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

Prefer YAML profiles for structured reusable defaults and `--yaml-parameter`
or `--domain-yaml-parameter` for per-run overrides.

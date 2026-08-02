# PAF Automation Domains

Each subdirectory is a reusable automation sphere. A domain groups PAF tasks
and XML scenarios by the kind of work being automated, not by one temporary
debug task.

Follow this contract for new domains:

```text
domains/<domain>/
  README.md
  tasks.py              # domain-owned PAF task classes
  domain.yaml           # optional domain metadata and defaults
  schema.yaml           # optional domain YAML schema
  scenarios/*.xml       # runnable scenario definitions
  profiles/*            # optional target/environment presets
  templates/*           # optional task-local starting points
  lib/                  # reusable Python implementation used by PAF tasks
  assets/               # non-PAF support code/assets owned by the domain
```

Keep the domain directory as the single source of truth for its reusable
automation. If compatibility requires an old Python import namespace, make that
namespace a thin shim that re-exports the domain-owned tasks.

Use `assets/` for support code that is not itself a PAF task, scenario,
profile, or template, for example Zephyr modules, Yocto layers, policy
snippets, fixtures, or target-side helpers. Do not create ad hoc sibling
directories such as `harness/` for support material.

Use `lib/` for ordinary Python implementation that PAF tasks call through
static imports. Keep `tasks.py` as the PAF-facing entry point instead of
placing scenario execution logic in shell scripts.

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

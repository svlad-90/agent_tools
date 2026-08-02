# codex_tools Findings

These findings apply to workspace-local tools such as `task_check`,
`diff_report`, `code_map`, `cpp_code_map`, `yaml_map`, reusable environments,
and workspace skills.

## Xen harness scheduled serial switching writes text, not bytes

The Xen/QEMU harness can schedule Xen serial input switches with
`--xen-switch-at`. This sends the doubled QEMU stdio-mux escape sequence needed
to deliver three Ctrl-A bytes to Xen, which then cycles input between Xen and
guest domains.

Known failure shape:

- A Xen/QEMU run is launched through the Xen/Zephyr PAF domain runtime tasks
  with one or more `--xen-switch-at` arguments.
- The harness opens the subprocess `stdin` in text mode.
- If the switch sequence is written as `bytes`, Python raises
  `TypeError: write() argument must be str, not bytes`.
- The runtime may fail before useful guest console evidence is collected,
  making it look like QEMU or the product failed early.

Practical checklist:

- Keep the raw Ctrl-A byte sequence for documentation and exactness, but decode
  it with a single-byte encoding such as Latin-1 before writing to text-mode
  `stdin`.
- If scheduled switching breaks, validate the runtime task file with:
  `python -m codex_tools.code_map parse-check codex_tools/paf_workspace/domains/xen-zephyr/runtime_tasks.py`.
- After the fix, verify the runtime log contains Xen switch markers such as
  `Serial input to DOM1` and `Serial input to DOM2` before relying on guest
  console conclusions.

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
- If scheduled switching breaks, validate the runtime support file with:
  `python -m codex_tools.tools.code_map parse-check codex_tools/paf_workspace/domains/xen_zephyr/lib/runtime.py`.
- After the fix, verify the runtime log contains Xen switch markers such as
  `Serial input to DOM1` and `Serial input to DOM2` before relying on guest
  console conclusions.

## cpp_code_map must be checked inside the selected build container

`cpp_code_map` depends on the same compiler paths, generated headers, sysroots,
and Python/libclang bindings that the target build uses. Host-side success does
not prove the tool will work inside a Zephyr, Yocto, or product build
container.

Known failure shape:

- A host command such as `python -m codex_tools.tools.cpp_code_map map ...`
  works on a small file.
- The real task later runs inside a Docker-backed build environment and fails
  for a different reason: missing image, missing `clang.cindex`, wrong workspace
  mount path, host-absolute source paths, or a compile database that points at
  paths not visible in the container.
- Agents then debug C/C++ source while the actual problem is the execution
  substrate.

Practical checklist:

- Run the environments PAF preflight before relying on C/C++ source analysis:
  `codex_tools/paf_workspace/run-paf.sh codex_tools/paf_workspace/domains/environments/scenarios/cpp-code-map.xml check-only --yaml-config codex_tools/paf_workspace/domains/environments/profiles/cpp-code-map-zephyr-xen.yaml --parameter CPP_CODE_MAP_SOURCE=<file> --parameter CPP_CODE_MAP_COMPILE_DB=<build-or-json>`.
- For a direct tool diagnostic, run
  `python -m codex_tools.tools.cpp_code_map doctor <file> --compile-db <build-or-json> --json`.
  When `--compile-db` is supplied but the file has no matching entry, treat
  that as an environment/build-context fault. Generic clang fallback is
  intentionally explicit via `--allow-fallback`.
- Treat `image_check` failure as an environment blocker and build/ensure the
  declared image before debugging source parsing.
- Pass workspace-relative paths when possible. The PAF task remaps those paths
  to the selected container mount before invoking
  `python3 -m codex_tools.tools.cpp_code_map`.
- If the compile database already uses absolute paths visible inside the
  container, do not remap them again. Remapping an existing `/workspace/...`
  path can make `cpp_code_map` miss the compile database entry and silently fall
  back to generic parser arguments.
- When a compile database is provided, the preflight validates the source entry,
  entry working directory, source file, compiler, include directories, and
  sysroot paths before libclang runs. Use the JSON report from
  `CPP_CODE_MAP_REPORT` as the first diagnostic artifact.
- When no source is provided, the preflight generates a tiny C++ fixture and
  still runs `map` plus `parse-check`; this catches broken Python/libclang
  bindings even before a target build exists.
- When the C/C++ build environment is not yet formalized or stable, use
  `python -m codex_tools.tools.cpp_light_code_map diagnose <file> --json` and
  `outline --compact` as the primary first-pass navigation tools. The light
  tool requires `tree-sitter` and `tree-sitter-cpp`. Its output is
  structural-only: it can provide diagnostics, unmapped tree-sitter coverage,
  outlines, filtered symbols, tree-sitter includes and macros, rough symbol
  spans, hashes, structural call lists, call-graph edges, scoped and
  categorized identifier references, locals, simple complexity metrics, cached
  workspace indexes, and guarded structural edits, but it does not validate
  types or compilation.
- Once the checkout, generated headers, container/toolchain, and
  `compile_commands.json` are settled, promote precise C/C++ source analysis
  and guarded edits to build-backed `cpp_code_map`.
- Useful light-map commands for fast triage:
  `diagnose --json`, `unmapped --json`, `outline --compact`, `symbols --kind
  function --name <text>`, `symbol-get --with-doc --json`, `calls --symbol
  <name> --json`, `call-graph --json`, `refs --name <identifier> --scope
  <symbol> --json`, `locals --symbol <name> --json`, `complexity --symbol
  <name> --json`, `index-dir ... --cache-dir <dir>`, `query --name <name>
  --cache-dir <dir>`, and guarded `rename-symbol --check-only`.

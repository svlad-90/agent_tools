# Environments PAF Domain

This domain owns reusable execution substrates: Docker images, container
aliases, toolchain smoke checks, and build commands that are shared by product
domains. Product domains should reference container aliases from this domain
instead of calling shell scripts under `codex_tools/environments`.

The domain exposes:

```text
tasks/        PAF task package
  __init__.py compatibility exports for existing task names
  base.py     shared image/container helpers
  zephyr_xen.py
  act.py
lib/          Python command builders used by tasks
assets/       Dockerfiles and environment source assets
scenarios/    runnable environment checks
profiles/     reusable environment YAML profiles
```

Environment entries:

- `zephyr-xen` provides a Zephyr SDK, west, CMake, Ninja, QEMU, Python clang
  bindings for `cpp_code_map`, and tree-sitter bindings for
  `cpp_light_code_map`. The default container alias is `zephyr-xen-workspace`,
  with the host workspace mounted at `/workspace`. Keep this image on Ubuntu
  24.04 unless its Dockerfile installs Python 3.12 explicitly; current Zephyr
  checkouts require Python 3.12.
- `yocto-xen` provides the Poky/kirkstone Xen product build environment. Keep
  this image on Ubuntu 22.04 so kirkstone uses its expected Python 3.10 host
  baseline.
- `codex-tools-act` provides an act driver image for running this repository's
  GitHub Actions workflows locally. It mounts the host Docker socket and the
  workspace.
- `moulin-act` provides the `ubuntu-22.04` act runner image used by Moulin's
  build workflow.
- `zephyr-xenlib-act` provides the `ubuntu-22.04` act runner image used by the
  zephyr-xenlib build workflow.

Every image declared in `domain.yaml` must declare `capabilities`. The
capabilities are defined in `lib/capabilities.py`; they drive Dockerfile
dependency tests and runtime smoke commands:

- `workspace_tools` is required for every image. It requires `bash`,
  `ca-certificates`, `git`, `python3`, `python3-pip`, `python3-venv`, and
  importable `tree_sitter` plus `tree_sitter_cpp` for `cpp_light_code_map`.
- `cpp_source_analysis` is required for images used for C/C++ build or source
  analysis. It requires `clang`, `libclang-dev`, and `python3-clang` so
  `cpp_code_map` can run in the same container as the build.

Ubuntu 24.04 images should use an explicit virtual environment in `PATH` when
installing Python packages with `pip`.

Run a check-only scenario with:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/environments/scenarios/<environment>.xml \
  check-only \
  --yaml-config codex_tools/paf_workspace/domains/environments/profiles/<environment>.yaml
```

Run validation with the same scenario and profile, replacing `check-only` with
`validate`. Use PAF `--parameter KEY=VALUE` overrides for task-local checkout
paths, token files, target filters, and extra act arguments.

Run `cpp_code_map` preflight inside an environment with:

```sh
codex_tools/paf_workspace/run-paf.sh \
  codex_tools/paf_workspace/domains/environments/scenarios/cpp-code-map.xml \
  check-only \
  --yaml-config codex_tools/paf_workspace/domains/environments/profiles/cpp-code-map-zephyr-xen.yaml \
  --parameter CPP_CODE_MAP_SOURCE=path/to/file.cpp \
  --parameter CPP_CODE_MAP_COMPILE_DB=path/to/build \
  --parameter CPP_CODE_MAP_REPORT=report/cpp-code-map-preflight.json
```

The task remaps workspace-relative or host-absolute paths to the selected
container mount before invoking `python3 -m codex_tools.tools.cpp_code_map`.
When `CPP_CODE_MAP_COMPILE_DB` is provided, it first validates that the source
has a compile database entry and that the entry's working directory, source
file, compiler, include directories, and sysroot paths exist inside the
container. It then runs `cpp_code_map doctor`, `map`, and `parse-check` in that
same container so argument selection is visible before libclang diagnostics are
interpreted. Without `CPP_CODE_MAP_SOURCE`, the same check parses a tiny
generated C++ fixture so the image still proves that `cpp_code_map`, Python
bindings, and libclang work together.

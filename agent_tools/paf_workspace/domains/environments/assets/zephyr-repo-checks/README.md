# Zephyr Repo Checks Environment Asset

This image is for Zephyr repository-level validation, not target runtime
validation. It extends `codex/zephyr-xen:24.04` with dependencies needed by
Zephyr PR checks:

- `python3-dev` for Python packages that compile extensions from
  `scripts/requirements-actions.txt`;
- Node/npm for CI helpers that use JavaScript tooling;
- `lcov`/`genhtml` for documentation coverage reports;
- Coccinelle for coding guideline checks.

Check an existing image through the environments PAF domain:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/environments/scenarios/cpp-code-map.xml \
  check-only \
  --yaml-config agent_tools/paf_workspace/domains/environments/profiles/zephyr-repo-checks.yaml
```

Build or rebuild the image with a scenario that includes an `ensure` phase:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/environments/scenarios/cpp-code-map.xml \
  validate \
  --yaml-config agent_tools/paf_workspace/domains/environments/profiles/zephyr-repo-checks.yaml \
  --parameter ENVIRONMENT_FORCE_IMAGE_REBUILD=1
```

When the base `zephyr-xen` image is not present, ensure that image first.

Repository-level validation entry points live in
`agent_tools/paf_workspace/domains/zephyr_repo_validation/`:

- `docs-coverage` generates Zephyr Doxygen coverage JSON with
  `ZEPHYR_DOCS_ZEPHYR` and `ZEPHYR_DOCS_BUILD_DIR`.
- `docs-diff` compares reference and PR coverage JSON with Zephyr's
  `doxygen_coverage_diff.py`, then checks the PR Doxygen XML directory with
  `doxygen_toplevel_groups.py`.
- `compliance` runs scoped `check_compliance.py` modules for formatting and
  file hygiene. The default set is `ClangFormat`, `GitDiffCheck`, `Checkpatch`,
  `BinaryFiles`, `TextEncoding`, `KconfigFormat`, `CMakeStyle`, and `YAMLLint`.
- `static-analysis` runs a normal Zephyr build task; pass
  `ZEPHYR_BUILD_CMAKE_ARGS=-DZEPHYR_SCA_VARIANT=gcc` to use Zephyr's GCC SCA
  integration.
- `codechecker-diff` runs Zephyr's CodeChecker/cppcheck SCA integration on
  changed C/C++ source files from `ZEPHYR_REPO_CHECKS_COMMIT_RANGE`. It uses
  `cppcheck` by default; override
  `ZEPHYR_REPO_CHECKS_CODECHECKER_ANALYZERS` when clang-based CodeChecker
  analyzers are valid for the selected board/toolchain.

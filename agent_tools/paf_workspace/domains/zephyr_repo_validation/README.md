# Zephyr Repository Validation PAF Domain

This domain owns Zephyr repository validation policy and command construction.
It uses Docker images and container aliases from the `environments` domain, but
does not define execution substrates itself.

Use this domain for checks that understand Zephyr repository layout and CI
rules:

- Doxygen coverage generation and coverage diff checks;
- top-level Doxygen group checks;
- upstream-compatible `scripts/ci/check_compliance.py` runs for required PR
  compliance checks;
- Zephyr static analysis builds, currently through `-DZEPHYR_SCA_VARIANT=gcc`.
- scoped CodeChecker/cppcheck runs over changed C/C++ source files from a git
  commit range.

The `environments` domain remains responsible for Dockerfiles, image aliases,
container aliases, mount/env setup, and capability smoke checks.

Prepare a Zephyr west workspace when a global repository check needs the
modules declared by the checkout's `west.yml`:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/zephyr_repo_validation/scenarios/zephyr-repo-checks.xml \
  west-update \
  --yaml-config agent_tools/paf_workspace/domains/zephyr_repo_validation/profiles/zephyr-repo-checks.yaml \
  --parameter ZEPHYR_REPO_CHECKS_ZEPHYR=path/to/zephyr
```

The Docker image contains the tools needed to run `west`; it does not bake in
Zephyr modules. Module sources are tied to each checkout's manifest revision,
so they are populated in the task workspace with `west update`.

Generate Doxygen coverage:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/zephyr_repo_validation/scenarios/zephyr-repo-checks.xml \
  docs-coverage \
  --yaml-config agent_tools/paf_workspace/domains/zephyr_repo_validation/profiles/zephyr-repo-checks.yaml \
  --parameter ZEPHYR_DOCS_ZEPHYR=path/to/zephyr \
  --parameter ZEPHYR_DOCS_BUILD_DIR=tasks/<task>/report/zephyr-docs
```

Compare reference and PR Doxygen outputs:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/zephyr_repo_validation/scenarios/zephyr-repo-checks.xml \
  docs-diff \
  --yaml-config agent_tools/paf_workspace/domains/zephyr_repo_validation/profiles/zephyr-repo-checks.yaml \
  --parameter ZEPHYR_REPO_CHECKS_ZEPHYR=path/to/zephyr \
  --parameter ZEPHYR_REPO_CHECKS_DOCS_REFERENCE=report/base/doc-coverage.json \
  --parameter ZEPHYR_REPO_CHECKS_DOCS_COMPARISON=report/pr/doc-coverage.json \
  --parameter ZEPHYR_REPO_CHECKS_DOCS_XML_DIR=report/pr/doxygen-xml/xml \
  --parameter ZEPHYR_REPO_CHECKS_DOCS_SUMMARY=report/zephyr-doxygen-summary.md
```

Run the upstream-compatible required PR compliance checks:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/zephyr_repo_validation/scenarios/zephyr-repo-checks.xml \
  compliance \
  --yaml-config agent_tools/paf_workspace/domains/zephyr_repo_validation/profiles/zephyr-repo-checks.yaml \
  --parameter ZEPHYR_REPO_CHECKS_ZEPHYR=path/to/zephyr \
  --parameter ZEPHYR_REPO_CHECKS_COMMIT_RANGE=origin/main..HEAD \
  --parameter ZEPHYR_REPO_CHECKS_COMPLIANCE_OUTPUT=report/compliance.xml
```

By default this mirrors Zephyr's `Compliance Checks` workflow shape: run
`check_compliance.py` for the commit range while excluding `KconfigBasic`,
`SysbuildKconfigBasic`, and `ClangFormat`. `ClangFormat` is excluded here
because Zephyr runs style/guideline checks through a separate workflow. Override
with newline-separated `ZEPHYR_REPO_CHECKS_COMPLIANCE_MODULES` or
`ZEPHYR_REPO_CHECKS_COMPLIANCE_EXCLUDES` only when the task needs a different
scope.

Use the `compliance-with-west-update` scenario when the local checkout should
be expanded with manifest modules before running the same compliance command.

Run Zephyr's GCC static analyzer path as a build-backed check:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/zephyr_repo_validation/scenarios/zephyr-repo-checks.xml \
  static-analysis \
  --yaml-config agent_tools/paf_workspace/domains/zephyr_repo_validation/profiles/zephyr-repo-checks.yaml \
  --parameter ZEPHYR_BUILD_ZEPHYR=path/to/zephyr \
  --parameter ZEPHYR_BUILD_APP=path/to/app \
  --parameter ZEPHYR_BUILD_BOARD=board/name \
  --parameter ZEPHYR_BUILD_DIR=tasks/<task>/report/build-gcc-sca \
  --parameter ZEPHYR_BUILD_CMAKE_ARGS=-DZEPHYR_SCA_VARIANT=gcc
```

Run Zephyr's CodeChecker integration on changed C/C++ source files from a
commit range:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/zephyr_repo_validation/scenarios/zephyr-repo-checks.xml \
  codechecker-diff \
  --yaml-config agent_tools/paf_workspace/domains/zephyr_repo_validation/profiles/zephyr-repo-checks.yaml \
  --parameter ZEPHYR_REPO_CHECKS_COMMIT_RANGE=origin/main..HEAD \
  --parameter ZEPHYR_BUILD_ZEPHYR=path/to/zephyr \
  --parameter ZEPHYR_BUILD_APP=path/to/app \
  --parameter ZEPHYR_BUILD_BOARD=board/name \
  --parameter ZEPHYR_BUILD_DIR=tasks/<task>/report/build-codechecker
```

The default scope is changed `.c`, `.cc`, `.cpp`, and `.cxx` files reported by
`git diff --name-only --diff-filter=ACMR`. The task writes those files into a
CodeChecker skipfile allow-list and passes it through
`CODECHECKER_ANALYZE_OPTS=--ignore;<skipfile>`, because Zephyr's CMake wrapper
places analyze options before `compile_commands.json`. The default analyzer is
`cppcheck`, because clang-based CodeChecker backends can reject Zephyr SDK
GCC-only flags. Override with newline-separated
`ZEPHYR_REPO_CHECKS_CODECHECKER_ANALYZERS` when the selected board/toolchain
supports additional analyzer backends. Header-only diffs do not map reliably to
CodeChecker translation units by themselves; pass explicit newline-separated
`ZEPHYR_REPO_CHECKS_CODECHECKER_FILE_GLOBS` when a task has a known source-file
scope.

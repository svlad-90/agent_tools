"""Command builders for Zephyr repository validation."""

from __future__ import annotations

import shlex
from pathlib import Path


class ZephyrBuild:
    def __init__(
        self,
        zephyr: str,
        app: str,
        board: str,
        build_dir: str,
        cmake_args: tuple[str, ...] = (),
        kconfig_options: tuple[str, ...] = (),
        board_roots: tuple[str, ...] = (),
        modules: tuple[str, ...] = (),
        export_compile_commands: bool = False,
        mode: str = "west",
    ) -> None:
        self.zephyr = zephyr
        self.app = app
        self.board = board
        self.build_dir = build_dir
        self.cmake_args = cmake_args
        self.kconfig_options = kconfig_options
        self.board_roots = board_roots
        self.modules = modules
        self.export_compile_commands = export_compile_commands
        self.mode = mode


class ZephyrDocsCoverage:
    def __init__(
        self,
        zephyr: str,
        build_dir: str,
    ) -> None:
        self.zephyr = zephyr
        self.build_dir = build_dir


class ZephyrDocsDiff:
    def __init__(
        self,
        zephyr: str,
        reference_coverage: str,
        comparison_coverage: str,
        xml_dir: str,
        summary: str,
        reference_prefix: str = "",
        comparison_prefix: str = "",
        warn_paths: tuple[str, ...] = (),
    ) -> None:
        self.zephyr = zephyr
        self.reference_coverage = reference_coverage
        self.comparison_coverage = comparison_coverage
        self.xml_dir = xml_dir
        self.summary = summary
        self.reference_prefix = reference_prefix
        self.comparison_prefix = comparison_prefix
        self.warn_paths = warn_paths


class ZephyrCompliance:
    def __init__(
        self,
        zephyr: str,
        commit_range: str,
        output: str,
        modules: tuple[str, ...],
        excludes: tuple[str, ...] = (),
        jobs: int = 1,
    ) -> None:
        self.zephyr = zephyr
        self.commit_range = commit_range
        self.output = output
        self.modules = modules
        self.excludes = excludes
        self.jobs = jobs


class ZephyrWestUpdate:
    def __init__(
        self,
        zephyr: str,
        update_args: tuple[str, ...] = (),
    ) -> None:
        self.zephyr = zephyr
        self.update_args = update_args


class ZephyrCodeCheckerDiff:
    def __init__(
        self,
        build: ZephyrBuild,
        commit_range: str,
        file_globs: tuple[str, ...] = (),
        analyzers: tuple[str, ...] = ("cppcheck",),
        config_file: str = ".codechecker.yml",
        jobs: int = 1,
        export: str = "json",
        parse_exit_status: bool = True,
    ) -> None:
        self.build = build
        self.commit_range = commit_range
        self.file_globs = file_globs
        self.analyzers = analyzers
        self.config_file = config_file
        self.jobs = jobs
        self.export = export
        self.parse_exit_status = parse_exit_status


def _quote(value: str | Path) -> str:
    return shlex.quote(str(value))


def _kconfig_option_to_cmake_arg(option: str) -> str:
    if option.startswith("-D"):
        return option

    if "=" in option:
        name, value = option.split("=", 1)
    else:
        name, sep, value = option.partition(":")
        if not sep:
            raise ValueError("Kconfig options must use NAME=value or NAME:value")

    if not name or not value:
        raise ValueError("Kconfig options must have a non-empty name and value")
    return f"-D{name}={value}"


def _zephyr_cmake_args(build: ZephyrBuild) -> list[str]:
    zephyr_cmake_args = list(build.cmake_args)
    zephyr_cmake_args.extend(
        _kconfig_option_to_cmake_arg(option)
        for option in build.kconfig_options
    )
    if build.board_roots:
        zephyr_cmake_args.append("-DBOARD_ROOT=" + ";".join(build.board_roots))
    if build.modules:
        zephyr_cmake_args.append("-DZEPHYR_MODULES=" + ";".join(build.modules))
    if build.export_compile_commands:
        zephyr_cmake_args.append("-DCMAKE_EXPORT_COMPILE_COMMANDS=ON")
    return zephyr_cmake_args


def zephyr_validate_command(build: ZephyrBuild) -> str:
    zephyr_cmake_args = _zephyr_cmake_args(build)
    cmake_args = " ".join(_quote(arg) for arg in zephyr_cmake_args)
    if build.mode == "west" and cmake_args:
        cmake_args = " -- " + cmake_args

    zephyr = _quote(build.zephyr)
    app = _quote(build.app)
    board = _quote(build.board)
    build_dir = _quote(build.build_dir)

    if build.mode == "cmake":
        if cmake_args:
            cmake_args = " " + cmake_args

        return f"""
set -euo pipefail
cd {zephyr}
source ./zephyr-env.sh
cmake -S {app} \\
  -B {build_dir} \\
  -GNinja \\
  -DBOARD={board} \\
  -DZEPHYR_BASE="$${{PWD}}"{cmake_args}
ninja -C {build_dir}
""".strip()

    return f"""
set -euo pipefail
cd {zephyr}
source ./zephyr-env.sh
west build -p auto \\
  -b {board} \\
  -d {build_dir} \\
  {app}{cmake_args}
""".strip()


def zephyr_codechecker_diff_command(check: ZephyrCodeCheckerDiff) -> str:
    build = check.build
    zephyr_cmake_args = _zephyr_cmake_args(build)
    zephyr_cmake_args.extend(
        (
            "-DZEPHYR_SCA_VARIANT=codechecker",
            f"-DCODECHECKER_CONFIG_FILE={check.config_file}",
            f"-DCODECHECKER_ANALYZE_JOBS={check.jobs if check.jobs > 0 else 1}",
            f"-DCODECHECKER_EXPORT={check.export}",
        )
    )
    if check.parse_exit_status:
        zephyr_cmake_args.append("-DCODECHECKER_PARSE_EXIT_STATUS=ON")

    cmake_array = "\n".join(f"  {_quote(arg)}" for arg in zephyr_cmake_args)
    zephyr = _quote(build.zephyr)
    app = _quote(build.app)
    board = _quote(build.board)
    build_dir = _quote(build.build_dir)
    commit_range = _quote(check.commit_range)
    explicit_globs = _quote("\n".join(check.file_globs))
    analyzers = ";".join(check.analyzers)
    analyzer_opts = ""
    if analyzers:
        analyzer_opts = (
            f'codechecker_analyze_opts="--analyzers;{analyzers};$codechecker_analyze_opts"'
        )

    if build.mode == "cmake":
        build_command = f"""
cmake -S {app} \\
  -B {build_dir} \\
  -GNinja \\
  -DBOARD={board} \\
  -DZEPHYR_BASE="${{PWD}}" \\
  "${{cmake_args[@]}}"
ninja -C {build_dir}
""".strip()
    else:
        build_command = f"""
west build -p auto \\
  -b {board} \\
  -d {build_dir} \\
  {app} \\
  -- "${{cmake_args[@]}}"
""".strip()

    return f"""
set -euo pipefail
cd {zephyr}
source ./zephyr-env.sh
CODECHECKER_COMMIT_RANGE={commit_range}
CODECHECKER_EXPLICIT_GLOBS={explicit_globs}
codechecker_files=()
if [ -n "$CODECHECKER_EXPLICIT_GLOBS" ]; then
  while IFS= read -r file_glob; do
    [ -n "$file_glob" ] && codechecker_files+=("$file_glob")
  done <<< "$CODECHECKER_EXPLICIT_GLOBS"
else
  while IFS= read -r source_file; do
    [ -n "$source_file" ] && [ -f "$source_file" ] && codechecker_files+=("$PWD/$source_file")
  done < <(git diff --name-only --diff-filter=ACMR "$CODECHECKER_COMMIT_RANGE" -- '*.c' '*.cc' '*.cpp' '*.cxx')
fi
if [ "${{#codechecker_files[@]}}" -eq 0 ]; then
  echo "No changed C/C++ source files for CodeChecker in $CODECHECKER_COMMIT_RANGE"
  exit 0
fi
codechecker_scope_file="$(mktemp /tmp/zephyr-codechecker-scope.XXXXXX)"
for codechecker_file in "${{codechecker_files[@]}}"; do
  printf '+%s\\n' "$codechecker_file" >> "$codechecker_scope_file"
done
printf -- '-*\\n' >> "$codechecker_scope_file"
codechecker_analyze_opts="--ignore;$codechecker_scope_file"
{analyzer_opts}
cmake_args=(
{cmake_array}
  "-DCODECHECKER_ANALYZE_OPTS=$codechecker_analyze_opts"
)
{build_command}
""".strip()


def zephyr_docs_coverage_command(docs: ZephyrDocsCoverage) -> str:
    zephyr = _quote(docs.zephyr)
    build_dir = _quote(docs.build_dir)

    return f"""
set -euo pipefail
cd {zephyr}
source ./zephyr-env.sh
make -C doc BUILDDIR={build_dir} configure DOXYGEN_FORCE_SINGLE_THREAD=1
cmake --build {build_dir} --target doxygen-coverage-json
""".strip()


def zephyr_docs_diff_command(diff: ZephyrDocsDiff) -> str:
    zephyr = _quote(diff.zephyr)
    reference = _quote(diff.reference_coverage)
    comparison = _quote(diff.comparison_coverage)
    xml_dir = _quote(diff.xml_dir)
    summary = _quote(diff.summary)
    extra_args = []
    if diff.reference_prefix:
        extra_args.append(f"--strip-reference-prefix {_quote(diff.reference_prefix)}")
    if diff.comparison_prefix:
        extra_args.append(f"--strip-comparison-prefix {_quote(diff.comparison_prefix)}")
    warn_paths = diff.warn_paths or (
        "include/zephyr/dt-bindings",
        "include/zephyr/posix",
    )
    extra_args.extend(f"--warn-paths {_quote(path)}" for path in warn_paths)
    extra_arg_text = " \\\n  ".join(extra_args)
    if extra_arg_text:
        extra_arg_text = " \\\n  " + extra_arg_text

    return f"""
set -euo pipefail
cd {zephyr}
source ./zephyr-env.sh
test -s {reference}
test -s {comparison}
test -s {xml_dir}/index.xml
mkdir -p "$(dirname {summary})"
python3 scripts/ci/doxygen_coverage_diff.py \\
  --reference {reference} \\
  --comparison {comparison} \\
  --summary-file {summary}{extra_arg_text}
python3 scripts/ci/doxygen_toplevel_groups.py \\
  --xml-dir {xml_dir} \\
  >> {summary}
""".strip()


def zephyr_compliance_command(check: ZephyrCompliance) -> str:
    zephyr = _quote(check.zephyr)
    commit_range = _quote(check.commit_range)
    output = _quote(check.output)
    excludes = check.excludes
    if not check.modules and not excludes:
        excludes = (
            "KconfigBasic",
            "SysbuildKconfigBasic",
            "ClangFormat",
        )
    module_args = " ".join(f"-m {_quote(module)}" for module in check.modules)
    exclude_args = " ".join(f"-e {_quote(module)}" for module in excludes)
    check_args = " ".join(
        arg for arg in (module_args, exclude_args) if arg
    )
    jobs = str(check.jobs if check.jobs > 0 else 1)

    return f"""
set -euo pipefail
cd {zephyr}
source ./zephyr-env.sh
COMPLIANCE_OUTPUT={output}
export COMPLIANCE_OUTPUT
python3 -m venv --system-site-packages /tmp/zephyr-compliance-venv
. /tmp/zephyr-compliance-venv/bin/activate
pip install -q -r scripts/requirements-actions.txt --require-hashes
mkdir -p "$(dirname "$COMPLIANCE_OUTPUT")"
./scripts/ci/check_compliance.py \\
  --annotate \\
  --commits {commit_range} \\
  --output "$COMPLIANCE_OUTPUT" \\
  --parallel {jobs} \\
  {check_args}
python3 - <<'PY'
import os
import sys
import xml.etree.ElementTree as ET

tree = ET.parse(os.environ["COMPLIANCE_OUTPUT"])
failures = 0
errors = 0
for suite in tree.iter("testsuite"):
    failures += int(suite.attrib.get("failures", "0") or "0")
    errors += int(suite.attrib.get("errors", "0") or "0")
if failures or errors:
    print(f"Zephyr compliance reported failures={{failures}}, errors={{errors}}", file=sys.stderr)
    raise SystemExit(1)
PY
""".strip()


def zephyr_west_update_command(update: ZephyrWestUpdate) -> str:
    zephyr = _quote(update.zephyr)
    update_args = " ".join(_quote(arg) for arg in update.update_args)

    return f"""
set -euo pipefail
ZEPHYR_REPO={zephyr}
WORKSPACE_DIR="$(dirname "$ZEPHYR_REPO")"
MANIFEST_PATH="$(basename "$ZEPHYR_REPO")"
cd "$WORKSPACE_DIR"
if [ ! -d .west ]; then
  west init -l "$ZEPHYR_REPO"
fi
west config manifest.path "$MANIFEST_PATH"
source "$ZEPHYR_REPO/zephyr-env.sh"
west update {update_args}
""".strip()

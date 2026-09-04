from __future__ import annotations

from paf_workspace.domains.zephyr_repo_validation.lib import runtime


def test_zephyr_docs_diff_command_uses_upstream_script_arguments() -> None:
    command = runtime.zephyr_docs_diff_command(
        runtime.ZephyrDocsDiff(
            zephyr="/workspace/zephyr",
            reference_coverage="/workspace/base/doc-coverage.json",
            comparison_coverage="/workspace/pr/doc-coverage.json",
            xml_dir="/workspace/pr/doxygen-xml/xml",
            summary="/workspace/report/doxygen-summary.md",
            reference_prefix="/workspace/base",
            comparison_prefix="/workspace/pr",
        )
    )

    assert "scripts/ci/doxygen_coverage_diff.py" in command
    assert "--reference /workspace/base/doc-coverage.json" in command
    assert "--comparison /workspace/pr/doc-coverage.json" in command
    assert "--summary-file /workspace/report/doxygen-summary.md" in command
    assert "--strip-reference-prefix /workspace/base" in command
    assert "--strip-comparison-prefix /workspace/pr" in command
    assert "scripts/ci/doxygen_toplevel_groups.py" in command
    assert "--xml-dir /workspace/pr/doxygen-xml/xml" in command
    assert "--warn-paths include/zephyr/dt-bindings" in command
    assert "--warn-paths include/zephyr/posix" in command


def test_zephyr_compliance_command_defaults_to_upstream_required_excludes() -> None:
    command = runtime.zephyr_compliance_command(
        runtime.ZephyrCompliance(
            zephyr="/workspace/zephyr",
            commit_range="origin/main..HEAD",
            output="/workspace/report/compliance.xml",
            modules=(),
            jobs=1,
        )
    )

    assert "--commits origin/main..HEAD" in command
    assert "--output \"$COMPLIANCE_OUTPUT\"" in command
    assert "-e KconfigBasic" in command
    assert "-e SysbuildKconfigBasic" in command
    assert "-e ClangFormat" in command
    assert "-m ClangFormat" not in command
    assert "ET.parse(os.environ[\"COMPLIANCE_OUTPUT\"])" in command
    assert "raise SystemExit(1)" in command


def test_zephyr_compliance_command_accepts_explicit_modules() -> None:
    command = runtime.zephyr_compliance_command(
        runtime.ZephyrCompliance(
            zephyr="/workspace/zephyr",
            commit_range="origin/main..HEAD",
            output="/workspace/report/compliance.xml",
            modules=("ClangFormat", "GitDiffCheck"),
            excludes=(),
            jobs=1,
        )
    )

    assert "-m ClangFormat" in command
    assert "-m GitDiffCheck" in command
    assert "-e ClangFormat" not in command


def test_zephyr_west_update_command_uses_checkout_manifest() -> None:
    command = runtime.zephyr_west_update_command(
        runtime.ZephyrWestUpdate(
            zephyr="/workspace/tasks/example/dev/zephyr",
            update_args=("--narrow", "-o=--depth=1"),
        )
    )

    assert "ZEPHYR_REPO=/workspace/tasks/example/dev/zephyr" in command
    assert 'WORKSPACE_DIR="$(dirname "$ZEPHYR_REPO")"' in command
    assert 'west init -l "$ZEPHYR_REPO"' in command
    assert 'west config manifest.path "$MANIFEST_PATH"' in command
    assert 'source "$ZEPHYR_REPO/zephyr-env.sh"' in command
    assert "west update --narrow -o=--depth=1" in command


def test_zephyr_codechecker_diff_command_scopes_to_changed_sources() -> None:
    command = runtime.zephyr_codechecker_diff_command(
        runtime.ZephyrCodeCheckerDiff(
            build=runtime.ZephyrBuild(
                zephyr="/workspace/zephyr",
                app="/workspace/zephyr/samples/hello_world",
                board="qemu_cortex_m3",
                build_dir="/workspace/report/build-codechecker",
                mode="west",
            ),
            commit_range="origin/main..HEAD",
            jobs=2,
        )
    )

    assert "-DZEPHYR_SCA_VARIANT=codechecker" in command
    assert "-DCODECHECKER_CONFIG_FILE=.codechecker.yml" in command
    assert "-DCODECHECKER_ANALYZE_JOBS=2" in command
    assert "-DCODECHECKER_PARSE_EXIT_STATUS=ON" in command
    assert "git diff --name-only --diff-filter=ACMR" in command
    assert "'*.c' '*.cc' '*.cpp' '*.cxx'" in command
    assert "codechecker_scope_file=\"$(mktemp /tmp/zephyr-codechecker-scope.XXXXXX)\"" in command
    assert "printf '+%s\\n' \"$codechecker_file\"" in command
    assert "printf -- '-*\\n'" in command
    assert "codechecker_analyze_opts=\"--ignore;$codechecker_scope_file\"" in command
    assert "codechecker_analyze_opts=\"--analyzers;cppcheck;" in command
    assert "-DCODECHECKER_ANALYZE_OPTS=$codechecker_analyze_opts" in command


def test_zephyr_codechecker_diff_command_accepts_explicit_file_globs() -> None:
    command = runtime.zephyr_codechecker_diff_command(
        runtime.ZephyrCodeCheckerDiff(
            build=runtime.ZephyrBuild(
                zephyr="/workspace/zephyr",
                app="/workspace/app",
                board="qemu_cortex_m3",
                build_dir="/workspace/build",
                mode="cmake",
            ),
            commit_range="origin/main..HEAD",
            file_globs=("*/subsys/foo.c", "*/drivers/bar.cpp"),
            analyzers=("cppcheck", "clang-tidy"),
            parse_exit_status=False,
        )
    )

    assert "CODECHECKER_EXPLICIT_GLOBS='*/subsys/foo.c" in command
    assert "*/drivers/bar.cpp'" in command
    assert "codechecker_analyze_opts=\"--analyzers;cppcheck;clang-tidy;" in command
    assert "-DCODECHECKER_PARSE_EXIT_STATUS=ON" not in command
    assert "cmake -S /workspace/app" in command

"""Command builders for JUCE repository validation."""

from __future__ import annotations

import shlex


class JuceRepoValidation:
    def __init__(
        self,
        *,
        repo: str,
        build_dir: str,
        cmake_args: tuple[str, ...] = (),
        build_args: tuple[str, ...] = (),
        ctest_args: tuple[str, ...] = (),
        task_dir: str = "",
    ) -> None:
        self.repo = repo
        self.build_dir = build_dir
        self.cmake_args = cmake_args
        self.build_args = build_args
        self.ctest_args = ctest_args
        self.task_dir = task_dir


def juce_repo_validation_command(config: JuceRepoValidation) -> str:
    repo = _quote(config.repo)
    build_dir = _quote(config.build_dir)
    cmake_args = " ".join(_quote(arg) for arg in config.cmake_args)
    build_args = " ".join(_quote(arg) for arg in config.build_args)
    ctest_args = " ".join(_quote(arg) for arg in config.ctest_args)
    task_dir = _quote(config.task_dir)
    return f"""
set -euo pipefail
export PYTHONUNBUFFERED=1
REPO={repo}
BUILD_DIR={build_dir}
TASK_DIR={task_dir}

cd "$REPO"
export PYTHONPATH="$REPO:$REPO/../../../..:$REPO/../../../../agent_tools:${{PYTHONPATH:-}}"
git config --global --add safe.directory "$REPO"

echo "JUCE repo validation: repo=$REPO build=$BUILD_DIR"

echo "Check git whitespace"
git diff --check

echo "Configure CMake"
cmake -S . -B "$BUILD_DIR" -G Ninja -DCMAKE_EXPORT_COMPILE_COMMANDS=ON {cmake_args}

echo "Build CMake target set"
cmake --build "$BUILD_DIR" {build_args}

echo "Run CTest"
ctest --test-dir "$BUILD_DIR" --output-on-failure {ctest_args}

if [ -n "$TASK_DIR" ]; then
  echo "Run task_check --strict-warnings: $TASK_DIR"
  python3 -m agent_tools.paf_workspace.task_check "$TASK_DIR" --workspace "$WORKSPACE_ROOT" --strict-warnings
fi

echo "JUCE repo validation: passed"
""".strip()


def _quote(value: str) -> str:
    return shlex.quote(value)

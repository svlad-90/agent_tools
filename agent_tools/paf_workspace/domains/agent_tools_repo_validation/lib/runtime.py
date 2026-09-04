"""Command builders for Agent Tools repository validation."""

from __future__ import annotations

import shlex


class AgentToolsRepoValidation:
    def __init__(
        self,
        repo: str,
        task_dir: str = "",
        scope: str = "all",
        base_ref: str = "HEAD",
        pytest_targets: tuple[str, ...] = ("agent_tools",),
        require_real_gtk: bool = True,
    ) -> None:
        self.repo = repo
        self.task_dir = task_dir
        self.scope = scope
        self.base_ref = base_ref
        self.pytest_targets = pytest_targets
        self.require_real_gtk = require_real_gtk


def agent_tools_repo_validation_command(config: AgentToolsRepoValidation) -> str:
    repo = _quote(config.repo)
    task_dir = _quote(config.task_dir)
    scope = _quote(config.scope)
    base_ref = _quote(config.base_ref)
    pytest_targets = " ".join(_quote(target) for target in config.pytest_targets)
    require_real_gtk = "1" if config.require_real_gtk else "0"
    return f"""
set -euo pipefail
export PYTHONUNBUFFERED=1
REPO={repo}
TASK_DIR={task_dir}
SCOPE={scope}
BASE_REF={base_ref}
REQUIRE_REAL_GTK={require_real_gtk}
PYTEST_TARGETS=({pytest_targets})

cd "$REPO"
export PYTHONPATH="$REPO:$REPO/agent_tools"
git config --global --add safe.directory "$REPO"

echo "Agent Tools repo validation: repo=$REPO scope=$SCOPE"

echo "Check git whitespace"
git diff --check

echo "Resolve Python validation targets"
if [ "$SCOPE" = "changed" ]; then
  mapfile -t PY_FILES < <(git diff --name-only --diff-filter=ACMR "$BASE_REF" -- '*.py')
  mapfile -t UNTRACKED_PY_FILES < <(git ls-files --others --exclude-standard -- '*.py')
  PY_FILES+=("${{UNTRACKED_PY_FILES[@]}}")
else
  mapfile -t PY_FILES < <(git ls-files '*.py')
fi

if [ "${{#PY_FILES[@]}}" -gt 0 ]; then
  echo "Python files: ${{#PY_FILES[@]}}"
  python3 -m py_compile "${{PY_FILES[@]}}"
  CODE_MAP_FILES=()
  for path in "${{PY_FILES[@]}}"; do
    case "$path" in
      agent_tools/*.py) CODE_MAP_FILES+=("${{path#agent_tools/}}") ;;
    esac
  done
  if [ "${{#CODE_MAP_FILES[@]}}" -gt 0 ]; then
    (cd agent_tools && python3 -m agent_tools.tools.code_map parse-check "${{CODE_MAP_FILES[@]}}")
  else
    echo "No agent_tools Python files selected for code_map parse-check"
  fi
else
  echo "No Python files selected"
fi

if [ "${{#PYTEST_TARGETS[@]}}" -gt 0 ]; then
  echo "Run pytest targets: ${{PYTEST_TARGETS[*]}}"
  xvfb-run -a python3 -X faulthandler -m pytest -q --maxfail=1 -ra "${{PYTEST_TARGETS[@]}}"
else
  echo "Skip pytest: no targets configured"
fi

if [ -f agent_tools/agent_workspace/components/ui_contract/tests/run_smoke.py ]; then
  echo "Run UI contract smoke"
  UI_CONTRACT_ARGS=()
  if [ "$REQUIRE_REAL_GTK" = "1" ]; then
    UI_CONTRACT_ARGS+=(--require-real-gtk)
  fi
  xvfb-run -a python3 -m agent_tools.agent_workspace.components.ui_contract.tests.run_smoke "${{UI_CONTRACT_ARGS[@]}}"
fi

if [ -n "$TASK_DIR" ]; then
  echo "Run task_check --strict-warnings: $TASK_DIR"
  python3 -m agent_tools.paf_workspace.task_check "$TASK_DIR" --strict-warnings
else
  echo "Skip task_check: AGENT_TOOLS_VALIDATE_TASK_DIR is empty"
fi

echo "Agent Tools repo validation: passed"
""".strip()


def _quote(value: str) -> str:
    return shlex.quote(value)

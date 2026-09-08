"""Command builders for Minecraft repository validation."""

from __future__ import annotations

import shlex


class MinecraftRepoValidation:
    def __init__(
        self,
        *,
        repo: str,
        plugin_dir: str,
        task_dir: str = "",
        require_sqlite_bundle: bool = True,
        run_paper_smoke: bool = True,
        paper_version: str = "1.21.1",
        paper_smoke_timeout_sec: int = 180,
    ) -> None:
        self.repo = repo
        self.plugin_dir = plugin_dir
        self.task_dir = task_dir
        self.require_sqlite_bundle = require_sqlite_bundle
        self.run_paper_smoke = run_paper_smoke
        self.paper_version = paper_version
        self.paper_smoke_timeout_sec = paper_smoke_timeout_sec


def minecraft_repo_validation_command(config: MinecraftRepoValidation) -> str:
    repo = _quote(config.repo)
    plugin_dir = _quote(config.plugin_dir)
    task_dir = _quote(config.task_dir)
    require_sqlite_bundle = "1" if config.require_sqlite_bundle else "0"
    run_paper_smoke = "1" if config.run_paper_smoke else "0"
    paper_version = _quote(config.paper_version)
    paper_smoke_timeout_sec = str(config.paper_smoke_timeout_sec)
    return f"""
set -euo pipefail
export PYTHONUNBUFFERED=1
REPO={repo}
PLUGIN_DIR={plugin_dir}
TASK_DIR={task_dir}
REQUIRE_SQLITE_BUNDLE={require_sqlite_bundle}
RUN_PAPER_SMOKE={run_paper_smoke}
PAPER_VERSION={paper_version}
PAPER_SMOKE_TIMEOUT_SEC={paper_smoke_timeout_sec}
WORKSPACE_ROOT="$REPO/../../../.."

cd "$REPO"
export PYTHONPATH="$REPO:$WORKSPACE_ROOT:$WORKSPACE_ROOT/agent_tools:${{PYTHONPATH:-}}"
git config --global --add safe.directory "$REPO"

echo "Minecraft repo validation: repo=$REPO plugin=$PLUGIN_DIR"

echo "Check git whitespace"
git diff --check

echo "Validate extracted server configuration"
python3 scripts/validate_configs.py

echo "Build server assembly with missing private artifacts allowed"
python3 scripts/build_server.py --clean --allow-missing-artifacts

echo "Run Gradle tests and build plugin jar"
gradle --project-dir "$PLUGIN_DIR" test jar

JAR="$PLUGIN_DIR/build/libs/frontline-factions-0.1.0-SNAPSHOT.jar"
test -f "$JAR"

if [ "$REQUIRE_SQLITE_BUNDLE" = "1" ]; then
  echo "Check SQLite driver bundle in plugin jar"
  jar tf "$JAR" | grep -x 'META-INF/services/java.sql.Driver'
  jar tf "$JAR" | grep -x 'org/sqlite/JDBC.class'
  jar tf "$JAR" | grep -x 'org/sqlite/native/Windows/x86_64/sqlitejdbc.dll'
  jar tf "$JAR" | grep -x 'org/sqlite/native/Linux/x86_64/libsqlitejdbc.so'
fi

if [ "$RUN_PAPER_SMOKE" = "1" ]; then
  echo "Run Paper runtime smoke"
  python3 scripts/run_paper_smoke.py \\
    --skip-build \\
    --paper-version "$PAPER_VERSION" \\
    --timeout "$PAPER_SMOKE_TIMEOUT_SEC"
fi

if [ -n "$TASK_DIR" ]; then
  echo "Run task_check --strict-warnings: $TASK_DIR"
  (cd "$WORKSPACE_ROOT" && python3 -m agent_tools.paf_workspace.task_check "$TASK_DIR" --strict-warnings)
fi

echo "Minecraft repo validation: passed"
""".strip()


def _quote(value: str) -> str:
    return shlex.quote(value)

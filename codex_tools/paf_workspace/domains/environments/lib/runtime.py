"""Command builders for reusable execution environments."""

from __future__ import annotations

import shlex
from pathlib import Path


ZEPHYR_XEN_TOOL_CHECK_COMMAND = """
set -euo pipefail
west --version
python3 --version
python3 -m west --version
cmake --version | head -1
ninja --version
qemu-system-aarch64 --version | head -1
"$${ZEPHYR_SDK_INSTALL_DIR}/gnu/aarch64-zephyr-elf/bin/aarch64-zephyr-elf-gcc" --version | head -1
python3 - <<'PY'
import clang.cindex
print("clang.cindex ok")
PY
""".strip()


class ZephyrBuild:
    def __init__(
        self,
        zephyr: str,
        app: str,
        board: str,
        build_dir: str,
        cmake_args: tuple[str, ...] = (),
    ) -> None:
        self.zephyr = zephyr
        self.app = app
        self.board = board
        self.build_dir = build_dir
        self.cmake_args = cmake_args


class CodexToolsActRun:
    def __init__(self, workflow: str, runner_image: str, extra_args: tuple[str, ...] = ()) -> None:
        self.workflow = workflow
        self.runner_image = runner_image
        self.extra_args = extra_args


class MoulinActRun:
    def __init__(self, repo_root: str, runner_image: str, extra_args: tuple[str, ...] = ()) -> None:
        self.repo_root = repo_root
        self.runner_image = runner_image
        self.extra_args = extra_args


class ZephyrXenlibActRun:
    def __init__(
        self,
        repo_root: str,
        runner_image: str,
        token_file: str,
        targets: tuple[str, ...],
        project: str = "zephyr-dom0-xt",
        extra_args: tuple[str, ...] = (),
    ) -> None:
        self.repo_root = repo_root
        self.runner_image = runner_image
        self.token_file = token_file
        self.targets = targets
        self.project = project
        self.extra_args = extra_args


def _quote(value: str | Path) -> str:
    return shlex.quote(str(value))


def docker_dns_preflight_command(*, network: str) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--network",
        network,
        "ubuntu:24.04",
        "getent",
        "hosts",
        "archive.ubuntu.com",
    ]


def zephyr_validate_command(build: ZephyrBuild) -> str:
    cmake_args = " ".join(_quote(arg) for arg in build.cmake_args)
    if cmake_args:
        cmake_args = " " + cmake_args

    zephyr = _quote(build.zephyr)
    app = _quote(build.app)
    board = _quote(build.board)
    build_dir = _quote(build.build_dir)

    return f"""
set -euo pipefail
cd {zephyr}
source ./zephyr-env.sh
mkdir -p {build_dir}/Kconfig
python3 scripts/zephyr_module.py \\
  --zephyr-base="$PWD" \\
  --kconfig-out {build_dir}/Kconfig/Kconfig.modules \\
  --cmake-out {build_dir}/zephyr_modules.txt \\
  --sysbuild-kconfig-out {build_dir}/Kconfig/Kconfig.sysbuild.modules \\
  --sysbuild-cmake-out {build_dir}/sysbuild_modules.txt \\
  --settings-out {build_dir}/zephyr_settings.txt
cmake -GNinja \\
  -B {build_dir} \\
  -S {app} \\
  -DBOARD={board} \\
  -DZEPHYR_BASE="$PWD" \\
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON{cmake_args}
cmake --build {build_dir}
""".strip()


CODEX_TOOLS_ACT_TOOL_CHECK_COMMAND = """
set -euo pipefail
python3 --version
git --version
docker --version
act --version
""".strip()


ACT_RUNNER_TOOL_CHECK_COMMAND = """
set -euo pipefail
git --version
python3 --version
cmake --version | head -1 || true
ninja --version || true
""".strip()


ZEPHYR_XENLIB_ACT_TOOL_CHECK_COMMAND = """
set -euo pipefail
git --version
cmake --version | head -1
ninja --version
protoc --version
""".strip()


def codex_tools_act_validate_command(run: CodexToolsActRun) -> str:
    args = " ".join(_quote(arg) for arg in run.extra_args)
    if args:
        args = " " + args
    return (
        "act workflow_dispatch "
        f"-W {_quote(run.workflow)} "
        f"-P {_quote('ubuntu-latest=' + run.runner_image)} "
        "--container-architecture linux/amd64"
        f"{args}"
    )


def moulin_act_validate_command(run: MoulinActRun) -> str:
    args = " ".join(_quote(arg) for arg in run.extra_args)
    if args:
        args = " " + args
    return f"""
set -euo pipefail
cd {_quote(run.repo_root)}
act pull_request -j build --pull=false -P {_quote('ubuntu-22.04=' + run.runner_image)}{args}
""".strip()


def zephyr_xenlib_act_validate_command(run: ZephyrXenlibActRun) -> str:
    targets = run.targets or (
        "rcar_spider_ca55",
        "rcar_salvator_xs_m3",
        "rcar_h3ulcb_ca57",
        "qemu_cortex_a53",
    )
    args = " ".join(_quote(arg) for arg in run.extra_args)
    if args:
        args = " " + args
    target_lines = "\n".join(f"  {_quote(target)}" for target in targets)
    return f"""
set -euo pipefail
if [ ! -s {_quote(run.token_file)} ]; then
  echo "missing or empty token file: {_quote(run.token_file)}" >&2
  exit 1
fi
secret_file="$(mktemp)"
chmod 600 "${{secret_file}}"
trap 'rm -f "${{secret_file}}"' EXIT
printf 'GITHUB_TOKEN=%s\\n' "$(tr -d '\\r\\n' < {_quote(run.token_file)})" >"${{secret_file}}"
cd {_quote(run.repo_root)}
targets=(
{target_lines}
)
for target in "${{targets[@]}}"; do
  echo "Running zephyr-xenlib matrix: target=${{target}}, project={run.project}"
  act push -j build --pull=false --rm \\
    --secret-file "${{secret_file}}" \\
    -P {_quote('ubuntu-22.04=' + run.runner_image)} \\
    --matrix "target:${{target}}" \\
    --matrix "project:{run.project}"{args}
done
""".strip()

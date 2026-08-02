"""Command builders for reusable execution environments."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path


ZEPHYR_XEN_TOOL_CHECK_COMMAND = """
set -euo pipefail
west --version
cmake --version | head -1
ninja --version
qemu-system-aarch64 --version | head -1
"${ZEPHYR_SDK_INSTALL_DIR}/gnu/aarch64-zephyr-elf/bin/aarch64-zephyr-elf-gcc" --version | head -1
python3 - <<'PY'
import clang.cindex
print("clang.cindex ok")
PY
""".strip()


@dataclass(frozen=True)
class ZephyrBuild:
    zephyr: str
    app: str
    board: str
    build_dir: str
    cmake_args: tuple[str, ...] = ()


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

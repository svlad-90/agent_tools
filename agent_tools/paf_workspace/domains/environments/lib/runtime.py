"""Command builders for reusable execution environments."""

from __future__ import annotations

import shlex
from pathlib import Path

from paf_workspace.domains.environments.lib.capabilities import baseline_check_command


ZEPHYR_XEN_TOOL_CHECK_COMMAND = """
set -euo pipefail
west --version
python3 --version
python3 -m west --version
cmake --version | head -1
ninja --version
doxygen --version
dot -V
qemu-system-aarch64 --version | head -1
"$${ZEPHYR_SDK_INSTALL_DIR}/gnu/aarch64-zephyr-elf/bin/aarch64-zephyr-elf-gcc" --version | head -1
python3 - <<'PY'
import clang.cindex
print("clang.cindex ok")
PY
""".strip()


def cpp_code_map_check_command(
    *,
    source: str = "",
    compile_db: str = "",
    symbol: str = "",
    report: str = "",
) -> str:
    source_assignment = _quote(source)
    compile_db_assignment = _quote(compile_db)
    symbol_assignment = _quote(symbol)
    report_assignment = _quote(report)
    return f"""
set -euo pipefail
CPP_CODE_MAP_SOURCE={source_assignment}
CPP_CODE_MAP_COMPILE_DB={compile_db_assignment}
CPP_CODE_MAP_SYMBOL={symbol_assignment}
CPP_CODE_MAP_REPORT={report_assignment}
export CPP_CODE_MAP_SOURCE CPP_CODE_MAP_COMPILE_DB CPP_CODE_MAP_SYMBOL CPP_CODE_MAP_REPORT

{baseline_check_command(("workspace_tools", "cpp_source_analysis"))}

if [ -n "$CPP_CODE_MAP_SOURCE" ]; then
  test -e "$CPP_CODE_MAP_SOURCE"
  compile_db_args=()
  if [ -n "$CPP_CODE_MAP_COMPILE_DB" ]; then
    test -e "$CPP_CODE_MAP_COMPILE_DB"
    compile_db_args=(--compile-db "$CPP_CODE_MAP_COMPILE_DB")
  fi
  python3 - <<'PY'
import json
import os
from pathlib import Path
import shlex
import shutil
import sys


def report_and_exit(payload, code):
    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text)
    report_path = os.environ.get("CPP_CODE_MAP_REPORT")
    if report_path:
        path = Path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\\n", encoding="utf-8")
    raise SystemExit(code)


source = Path(os.environ["CPP_CODE_MAP_SOURCE"]).resolve()
compile_db_value = os.environ.get("CPP_CODE_MAP_COMPILE_DB", "")
payload = {{
    "source": str(source),
    "compile_db": compile_db_value,
    "checks": {{}},
    "missing": [],
}}
if not source.exists():
    payload["missing"].append({{"kind": "source", "path": str(source)}})
    report_and_exit(payload, 2)
if not compile_db_value:
    payload["checks"]["compile_db"] = "not provided"
    report_and_exit(payload, 0)

compile_db = Path(compile_db_value)
if compile_db.is_dir():
    compile_db = compile_db / "compile_commands.json"
compile_db = compile_db.resolve()
payload["compile_db"] = str(compile_db)
if not compile_db.exists():
    payload["missing"].append({{"kind": "compile_db", "path": str(compile_db)}})
    report_and_exit(payload, 2)

entries = json.loads(compile_db.read_text(encoding="utf-8"))
entry = None
for candidate in entries:
    directory = Path(candidate.get("directory", "."))
    if not directory.is_absolute():
        directory = compile_db.parent / directory
    file_path = Path(candidate.get("file", ""))
    if not file_path.is_absolute():
        file_path = directory / file_path
    if file_path.resolve() == source:
        entry = candidate
        entry_directory = directory.resolve()
        entry_file = file_path.resolve()
        break

payload["checks"]["compile_db_entries"] = len(entries)
if entry is None:
    payload["missing"].append({{
        "kind": "compile_db_entry",
        "source": str(source),
        "sample_files": [str(item.get("file", "")) for item in entries[:5]],
    }})
    report_and_exit(payload, 2)

payload["entry"] = {{
    "directory": str(entry_directory),
    "file": str(entry_file),
}}
if not entry_directory.exists():
    payload["missing"].append({{"kind": "directory", "path": str(entry_directory)}})
if not entry_file.exists():
    payload["missing"].append({{"kind": "file", "path": str(entry_file)}})

args = entry.get("arguments")
if args is None:
    args = shlex.split(entry.get("command", ""))
args = list(args)
payload["entry"]["argv0"] = args[0] if args else ""
if args:
    compiler = args[0]
    compiler_path = Path(compiler)
    compiler_ok = compiler_path.exists() if compiler_path.is_absolute() else shutil.which(compiler) is not None
    payload["checks"]["compiler"] = "ok" if compiler_ok else "missing"
    if not compiler_ok:
        payload["missing"].append({{"kind": "compiler", "path": compiler}})

include_options = {{"-I", "-isystem", "-iquote", "--sysroot"}}
index = 1
while index < len(args):
    arg = args[index]
    value = None
    if arg in include_options and index + 1 < len(args):
        value = args[index + 1]
        index += 2
    elif arg.startswith("-I") and len(arg) > 2:
        value = arg[2:]
        index += 1
    elif arg.startswith("-isystem") and len(arg) > len("-isystem"):
        value = arg[len("-isystem"):]
        index += 1
    elif arg.startswith("-iquote") and len(arg) > len("-iquote"):
        value = arg[len("-iquote"):]
        index += 1
    elif arg.startswith("--sysroot="):
        value = arg.split("=", 1)[1]
        index += 1
    else:
        index += 1
    if not value:
        continue
    path = Path(value)
    if not path.is_absolute():
        path = entry_directory / path
    if not path.exists():
        payload["missing"].append({{"kind": "include_or_sysroot", "path": str(path), "option": arg}})

payload["checks"]["compile_db_entry"] = "ok"
payload["checks"]["paths"] = "ok" if not payload["missing"] else "missing"
report_and_exit(payload, 2 if payload["missing"] else 0)
PY
  python3 -m agent_tools.tools.cpp_code_map doctor "$CPP_CODE_MAP_SOURCE" "${{compile_db_args[@]}}" --json
  python3 -m agent_tools.tools.cpp_code_map map "$CPP_CODE_MAP_SOURCE" "${{compile_db_args[@]}}"
  python3 -m agent_tools.tools.cpp_code_map parse-check "$CPP_CODE_MAP_SOURCE" "${{compile_db_args[@]}}"
  if [ -n "$CPP_CODE_MAP_SYMBOL" ]; then
    python3 -m agent_tools.tools.cpp_code_map symbol-get "$CPP_CODE_MAP_SOURCE" \\
      --symbol "$CPP_CODE_MAP_SYMBOL" "${{compile_db_args[@]}}" --json
  fi
else
  cat > /tmp/cpp_code_map_smoke.cpp <<'CPP'
int add(int left, int right)
{{
    return left + right;
}}
CPP
  cat > /tmp/compile_commands.json <<'JSON'
[
  {{
    "directory": "/tmp",
    "arguments": [
      "/usr/bin/c++",
      "-std=c++17",
      "-c",
      "/tmp/cpp_code_map_smoke.cpp",
      "-o",
      "cpp_code_map_smoke.o"
    ],
    "file": "/tmp/cpp_code_map_smoke.cpp"
  }}
]
JSON
  python3 -m agent_tools.tools.cpp_code_map map /tmp/cpp_code_map_smoke.cpp --compile-db /tmp
  python3 -m agent_tools.tools.cpp_code_map parse-check /tmp/cpp_code_map_smoke.cpp --compile-db /tmp
fi
""".strip()


def workspace_tool_baseline_check_command(capabilities: tuple[str, ...]) -> str:
    return baseline_check_command(capabilities)


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


class AgentToolsActRun:
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


def _kconfig_option_to_cmake_arg(option: str) -> str:
    if option.startswith("-D"):
        return option

    if "=" in option:
        name, value = option.split("=", 1)
    else:
        name, sep, value = option.partition(":")
        if not sep:
            raise ValueError(
                "Kconfig options must use NAME=value or NAME:value"
            )

    if not name or not value:
        raise ValueError("Kconfig options must have a non-empty name and value")
    return f"-D{name}={value}"


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


AGENT_TOOLS_ACT_TOOL_CHECK_COMMAND = """
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


def agent_tools_act_validate_command(run: AgentToolsActRun) -> str:
    args = " ".join(_quote(arg) for arg in run.extra_args)
    if args:
        args = " " + args
    return (
        "act pull_request "
        f"-W {_quote(run.workflow)} "
        f"-P {_quote('ubuntu-latest=' + run.runner_image)} "
        f"-P {_quote('ubuntu-24.04=' + run.runner_image)} "
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

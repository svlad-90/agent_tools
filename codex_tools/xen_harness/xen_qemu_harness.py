#!/usr/bin/env python3
"""Run Xen/QEMU commands and collect domain-oriented logs."""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path


XEN_SWITCH_BYTES = b"\x01\x01\x01\x01\x01\x01"
XEN_SWITCH_TEXT = XEN_SWITCH_BYTES.decode("latin1")
SERIAL_INPUT_RE = re.compile(r"\(XEN\) \*\*\* Serial input to DOM(\d+)")
HARNESS_DOMAIN_RE = re.compile(r"\[xen-harness\]\[(dom0|domu\d+|xen|host)\]")
XEN_GUEST_PREFIX_RE = re.compile(r"^\(d(\d+)\) ")
HOST_LINE_PREFIXES = (
    "qemu-system-",
)
ZEPHYR_XEN_QEMU_IMAGE = "xtbuilder-moulin-task-zephyr0163:latest"
ZEPHYR_XEN_QEMU_PRODUCT = Path(
    "zephyr-xenstore-client/dev/qemu-xen-zephyr-dom0-validation"
)
ZEPHYR_XEN_QEMU_QEMU_BIN = (
    "/home/builder/workspace/yocto/build-xen-qemu/tmp/work/x86_64-linux/"
    "qemu-system-native/7.0.0-r0/build/qemu-system-aarch64"
)
DEFAULT_DOMU_LOAD_ADDR = "0x59000000"


@dataclass(frozen=True)
class Expectation:
    source: str
    text: str


@dataclass
class ExpectationResult:
    expectation: Expectation
    found: bool = False


@dataclass
class SourceStats:
    lines: int = 0
    bytes: int = 0


@dataclass
class RunResult:
    return_code: int
    timed_out: bool
    stopped_on_match: bool
    expectation_results: list[ExpectationResult]
    source_stats: dict[str, SourceStats]


@dataclass(frozen=True)
class ZephyrBuild:
    zephyr: str
    app: str
    board: str
    build_dir: str
    cmake_args: tuple[str, ...] = ()


@dataclass(frozen=True)
class AbiExpectation:
    domctl: str
    sysctl: str
    source: str


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    log_file: str | None = None
    dom0_bin: str | None = None
    domu_bin: str | None = None
    timeout_sec: float | None = None
    preset: str | None = None
    expect: tuple[Expectation, ...] = ()
    require_source: tuple[str, ...] = ()
    domu_build: ZephyrBuild | None = None
    expected_abi: AbiExpectation | None = None
    domu_load_addr: str = DEFAULT_DOMU_LOAD_ADDR
    env: tuple[tuple[str, str], ...] = ()


def parse_key_value(value: str, option: str) -> tuple[str, str]:
    key, sep, item_value = value.partition("=")
    if not sep or not key:
        raise argparse.ArgumentTypeError(f"{option} must use KEY=VALUE")
    return key, item_value


def parse_expectation(value: str) -> Expectation:
    source, sep, text = value.partition(":")
    if not sep or not source or not text:
        raise argparse.ArgumentTypeError("--expect must use SOURCE:TEXT")
    return Expectation(source=source, text=text)


def require_string(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"scenario field {key!r} must be a non-empty string")
    return value


def optional_string(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"scenario field {key!r} must be a string")
    return value


def load_expectations(values: object) -> tuple[Expectation, ...]:
    if values is None:
        return ()
    if not isinstance(values, list):
        raise ValueError("scenario field 'expect' must be a list")

    expectations: list[Expectation] = []
    for index, value in enumerate(values):
        if not isinstance(value, dict):
            raise ValueError(f"scenario expect[{index}] must be an object")
        expectations.append(
            Expectation(
                source=require_string(value, "source"),
                text=require_string(value, "text"),
            )
        )
    return tuple(expectations)


def load_string_list(data: dict[str, object], key: str) -> tuple[str, ...]:
    values = data.get(key)
    if values is None:
        return ()
    if not isinstance(values, list):
        raise ValueError(f"scenario field {key!r} must be a list")
    if not all(isinstance(value, str) for value in values):
        raise ValueError(f"scenario field {key!r} must contain only strings")
    return tuple(values)


def load_env(values: object) -> tuple[tuple[str, str], ...]:
    if values is None:
        return ()
    if not isinstance(values, dict):
        raise ValueError("scenario field 'env' must be an object")

    env: list[tuple[str, str]] = []
    for key, value in values.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("scenario env keys and values must be strings")
        env.append((key, value))
    return tuple(env)


def load_zephyr_build(data: object) -> ZephyrBuild | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("scenario field 'domu_build' must be an object")

    return ZephyrBuild(
        zephyr=require_string(data, "zephyr"),
        app=require_string(data, "app"),
        board=require_string(data, "board"),
        build_dir=require_string(data, "build_dir"),
        cmake_args=load_string_list(data, "cmake_args"),
    )


def load_abi_expectation(data: object) -> AbiExpectation | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("scenario field 'expected_abi' must be an object")

    return AbiExpectation(
        domctl=require_string(data, "domctl"),
        sysctl=require_string(data, "sysctl"),
        source=require_string(data, "source"),
    )


def load_scenario(path: Path) -> Scenario:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("scenario file must contain a JSON object")

    timeout = data.get("timeout_sec")
    if timeout is not None and not isinstance(timeout, (int, float)):
        raise ValueError("scenario field 'timeout_sec' must be a number")

    return Scenario(
        name=require_string(data, "name"),
        description=optional_string(data, "description") or "",
        log_file=optional_string(data, "log_file"),
        dom0_bin=optional_string(data, "dom0_bin"),
        domu_bin=optional_string(data, "domu_bin"),
        timeout_sec=float(timeout) if timeout is not None else None,
        preset=optional_string(data, "preset"),
        expect=load_expectations(data.get("expect")),
        require_source=load_string_list(data, "require_source"),
        domu_build=load_zephyr_build(data.get("domu_build")),
        expected_abi=load_abi_expectation(data.get("expected_abi")),
        domu_load_addr=optional_string(data, "domu_load_addr") or DEFAULT_DOMU_LOAD_ADDR,
        env=load_env(data.get("env")),
    )


def append_env(args: argparse.Namespace, key: str, value: str | None) -> None:
    if value is None:
        return
    args.env = [item for item in args.env if item[0] != key]
    args.env.append((key, value))


def append_expectations(
    args: argparse.Namespace,
    expectations: tuple[Expectation, ...],
) -> None:
    existing = {(item.source, item.text) for item in args.expect}
    for expectation in expectations:
        key = (expectation.source, expectation.text)
        if key not in existing:
            args.expect.append(expectation)
            existing.add(key)


def workspace_root(args: argparse.Namespace) -> Path:
    if args.workspace_root:
        return args.workspace_root.resolve()
    return Path.cwd().resolve()


def resolve_workspace_path(path_text: str, root: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path.resolve()
    return (root / path).resolve()


def docker_path(path_text: str, root: Path, product_dir: Path) -> str:
    path = resolve_workspace_path(path_text, root)

    try:
        return str(Path("/home/builder/workspace") / path.relative_to(product_dir))
    except ValueError:
        pass

    try:
        return str(Path("/workspace") / path.relative_to(root))
    except ValueError:
        return path_text


def apply_scenario(args: argparse.Namespace) -> None:
    if not args.scenario_file:
        return

    scenario = load_scenario(args.scenario_file)
    args.scenario_config = scenario
    args.preset = args.preset or scenario.preset
    if not args.log_file and scenario.log_file:
        args.log_file = Path(scenario.log_file)
    args.timeout_sec = args.timeout_sec or scenario.timeout_sec
    args.dom0_bin = args.dom0_bin or scenario.dom0_bin
    args.domu_bin = args.domu_bin or scenario.domu_bin
    args.domu_load_addr = args.domu_load_addr or scenario.domu_load_addr
    append_expectations(args, scenario.expect)
    for source in scenario.require_source:
        if source not in args.require_source:
            args.require_source.append(source)


def apply_scenario_env(args: argparse.Namespace) -> None:
    scenario = getattr(args, "scenario_config", None)
    if scenario is None:
        return

    for key, value in scenario.env:
        append_env(args, key, value)


def apply_zephyr_xen_qemu_preset(args: argparse.Namespace) -> None:
    root = workspace_root(args)
    product_dir = (root / args.product_dir).resolve()

    if not args.docker_image:
        args.docker_image = ZEPHYR_XEN_QEMU_IMAGE
    if not args.docker_workdir:
        args.docker_workdir = "/home/builder/workspace"
    if not args.cmd:
        args.cmd = "bash ./scripts/gen-xen-dtb.sh /tmp/xen-qemu-harness.yaml >/dev/null && ./run/run-qemu.sh"

    product_mount = f"{product_dir}:/home/builder/workspace"
    workspace_mount = f"{root}:/workspace"
    for mount in (product_mount, workspace_mount):
        if mount not in args.mount:
            args.mount.append(mount)

    append_env(args, "QEMU_BIN", args.qemu_bin or ZEPHYR_XEN_QEMU_QEMU_BIN)
    append_env(args, "XEN_STATIC_DOMU", args.xen_static_domu)
    append_env(args, "XEN_LOAD_DOMU_IMAGE", args.xen_load_domu_image)
    append_env(args, "DOMU_LOAD_ADDR", args.domu_load_addr)

    if args.dom0_bin:
        append_env(args, "DOM0_BIN", docker_path(args.dom0_bin, root, product_dir))
    if args.domu_bin:
        append_env(args, "DOMU_BIN", docker_path(args.domu_bin, root, product_dir))
    if args.xen_dtb:
        append_env(args, "XEN_DTB", docker_path(args.xen_dtb, root, product_dir))


def apply_presets(args: argparse.Namespace) -> None:
    apply_scenario(args)
    if args.preset == "zephyr-xen-qemu":
        apply_zephyr_xen_qemu_preset(args)
    apply_scenario_env(args)


def run_zephyr_build(build: ZephyrBuild, root: Path) -> int:
    command = [
        str(root / "codex_tools/environments/zephyr-xen/scripts/validate.sh"),
        "--zephyr",
        build.zephyr,
        "--app",
        build.app,
        "--board",
        build.board,
        "--build-dir",
        build.build_dir,
    ]
    for cmake_arg in build.cmake_args:
        command.extend(["--cmake-arg", cmake_arg])

    print("build: " + " ".join(command), flush=True)
    return subprocess.run(command, cwd=root).returncode


def read_config_value(path: Path, name: str) -> str | None:
    if not path.exists():
        return None

    define_re = re.compile(rf"^#define {re.escape(name)}\s+(\S+)")
    cache_re = re.compile(rf"^{re.escape(name)}:[^=]*=(\S+)")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        define_match = define_re.match(line)
        if define_match:
            return define_match.group(1)
        cache_match = cache_re.match(line)
        if cache_match:
            return cache_match.group(1)
    return None


def zephyr_build_dir_from_bin(bin_path: Path) -> Path:
    if bin_path.name != "zephyr.bin" or bin_path.parent.name != "zephyr":
        raise ValueError(f"cannot infer Zephyr build directory from {bin_path}")
    return bin_path.parent.parent


def preflight(args: argparse.Namespace) -> int:
    if args.skip_preflight:
        return 0

    root = workspace_root(args)
    if not args.dom0_bin or not args.domu_bin:
        return 0

    scenario = getattr(args, "scenario_config", None)
    dom0_bin = resolve_workspace_path(args.dom0_bin, root)
    domu_bin = resolve_workspace_path(args.domu_bin, root)
    for label, path in (("Dom0", dom0_bin), ("DomU", domu_bin)):
        if not path.exists():
            print(f"preflight: {label} binary is missing: {path}", file=sys.stderr)
            return 1

    domu_size = domu_bin.stat().st_size
    try:
        dom0_build_dir = zephyr_build_dir_from_bin(dom0_bin)
    except ValueError as error:
        print(f"preflight: {error}", file=sys.stderr)
        return 1

    dom0_cache = dom0_build_dir / "CMakeCache.txt"
    dom0_autoconf = dom0_build_dir / "zephyr/include/generated/zephyr/autoconf.h"
    configured_size = read_config_value(dom0_cache, "XEN_HARNESS_DOMU_IMAGE_SIZE")
    configured_addr = read_config_value(dom0_cache, "XEN_HARNESS_DOMU_IMAGE_LOAD_ADDR")
    print(f"preflight: DomU image size {domu_size} bytes")
    if configured_size is not None:
        print(f"preflight: Dom0 configured DomU image size {configured_size} bytes")
        if int(configured_size, 0) != domu_size:
            print(
                "preflight: Dom0 was built for a different DomU image size; "
                "rebuild Dom0 harness image",
                file=sys.stderr,
            )
            return 1

    if configured_addr is not None and args.domu_load_addr:
        print(f"preflight: Dom0 DomU load address {configured_addr}")
        if int(configured_addr, 0) != int(args.domu_load_addr, 0):
            print(
                "preflight: Dom0 DomU load address does not match harness "
                f"DOMU_LOAD_ADDR={args.domu_load_addr}",
                file=sys.stderr,
            )
            return 1

    if scenario and scenario.expected_abi:
        actual_domctl = read_config_value(
            dom0_autoconf,
            "CONFIG_XEN_DOMCTL_INTERFACE_VERSION",
        )
        actual_sysctl = read_config_value(
            dom0_autoconf,
            "CONFIG_XEN_SYSCTL_INTERFACE_VERSION",
        )
        expected = scenario.expected_abi
        print(
            "preflight: Dom0 ABI "
            f"domctl {actual_domctl or 'missing'}, sysctl {actual_sysctl or 'missing'}"
        )
        print(
            "preflight: expected ABI "
            f"domctl {expected.domctl}, sysctl {expected.sysctl} ({expected.source})"
        )
        if actual_domctl != expected.domctl or actual_sysctl != expected.sysctl:
            print("preflight: Dom0 control ABI mismatch", file=sys.stderr)
            return 1

    return 0


def prepare_inputs(args: argparse.Namespace) -> int:
    root = workspace_root(args)
    scenario = getattr(args, "scenario_config", None)
    if scenario and scenario.domu_build and not args.skip_build:
        build_rc = run_zephyr_build(scenario.domu_build, root)
        if build_rc != 0:
            return build_rc
    return preflight(args)


def build_command(args: argparse.Namespace) -> list[str] | str:
    if not args.docker_image:
        return args.cmd

    command = ["docker", "run", "--rm", "-i"]
    for mount in args.mount:
        command.extend(["-v", mount])
    if args.docker_workdir:
        command.extend(["-w", args.docker_workdir])
    for key, value in args.env:
        command.extend(["-e", f"{key}={value}"])
    command.extend([args.docker_image, "bash", "-lc", args.cmd])
    return command


def all_markers_found(
    expectation_results: list[ExpectationResult],
    required_sources: list[str],
    source_stats: dict[str, SourceStats],
) -> bool:
    if not expectation_results and not required_sources:
        return False
    return all(item.found for item in expectation_results) and all(
        source_stats.get(source, SourceStats()).bytes > 0
        for source in required_sources
    )


def write_stdin_events(
    stdin: object,
    switch_times: list[float],
    timeout_sec: float,
) -> None:
    started = time.monotonic()
    for switch_time in sorted(switch_times):
        delay = started + switch_time - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        try:
            stdin.write(XEN_SWITCH_TEXT)
            stdin.flush()
        except BrokenPipeError:
            return

    remaining = started + timeout_sec - time.monotonic()
    if remaining > 0:
        time.sleep(remaining)
    try:
        stdin.close()
    except BrokenPipeError:
        pass


def enqueue_output(stdout: object, lines: queue.Queue[str]) -> None:
    for line in stdout:
        lines.put(line)


def terminate_process(process: subprocess.Popen[object]) -> int:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return process.wait()
    try:
        return process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return process.wait()


def run_command(args: argparse.Namespace) -> RunResult:
    command = build_command(args)
    shell = not args.docker_image
    cwd = args.cwd if not args.docker_image else None
    timed_out = False
    stopped_on_match = False
    active_guest: str | None = None
    source_stats: dict[str, SourceStats] = {}
    expectation_results = [ExpectationResult(expectation) for expectation in args.expect]
    line_queue: queue.Queue[str] = queue.Queue()
    deadline = time.monotonic() + args.timeout_sec

    args.log_file.parent.mkdir(parents=True, exist_ok=True)
    with args.log_file.open("w", errors="replace") as output:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            shell=shell,
            start_new_session=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            bufsize=1,
        )
        assert process.stdin is not None
        assert process.stdout is not None
        stdin_thread = threading.Thread(
            target=write_stdin_events,
            args=(process.stdin, args.xen_switch_at, args.timeout_sec),
            daemon=True,
        )
        stdout_thread = threading.Thread(
            target=enqueue_output,
            args=(process.stdout, line_queue),
            daemon=True,
        )
        stdin_thread.start()
        stdout_thread.start()

        while True:
            try:
                line = line_queue.get(timeout=0.1)
            except queue.Empty:
                if process.poll() is not None and line_queue.empty():
                    return_code = process.returncode
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    return_code = terminate_process(process)
                    break
                continue

            source, active_guest = source_for_line(line, active_guest)
            prefixed_line = f"[{source}] {line}"
            output.write(prefixed_line)
            output.flush()

            stats = source_stats.setdefault(source, SourceStats())
            stats.lines += 1
            stats.bytes += len(line.encode(errors="replace"))

            for result in expectation_results:
                expectation = result.expectation
                if expectation.source == source and expectation.text in line:
                    result.found = True
                if expectation.source == "combined" and expectation.text in prefixed_line:
                    result.found = True
                if expectation.source == "raw" and expectation.text in line:
                    result.found = True

            if not args.no_stop_on_match and all_markers_found(
                expectation_results,
                args.require_source,
                source_stats,
            ):
                stopped_on_match = True
                return_code = terminate_process(process)
                break

        stdin_thread.join(timeout=1)
        stdout_thread.join(timeout=1)

    if timed_out:
        return_code = 124
    return RunResult(
        return_code=return_code,
        timed_out=timed_out,
        stopped_on_match=stopped_on_match,
        expectation_results=expectation_results,
        source_stats=source_stats,
    )


def source_for_line(line: str, active_guest: str | None) -> tuple[str, str | None]:
    match = SERIAL_INPUT_RE.search(line)
    next_guest = active_guest
    if match:
        domain_id = match.group(1)
        next_guest = "dom0" if domain_id == "0" else f"domu{domain_id}"

    harness_domain = HARNESS_DOMAIN_RE.search(line)
    if harness_domain:
        return harness_domain.group(1), next_guest
    xen_guest_prefix = XEN_GUEST_PREFIX_RE.match(line)
    if xen_guest_prefix:
        return f"domu{xen_guest_prefix.group(1)}", next_guest
    if line.startswith("(XEN)"):
        return "xen", next_guest
    if line.startswith(HOST_LINE_PREFIXES):
        return "host", next_guest
    if active_guest:
        return active_guest, next_guest
    return "unknown", next_guest


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario-file",
        type=Path,
        help="Load task-owned Xen/Zephyr scenario JSON.",
    )
    parser.add_argument("--log-file", type=Path)
    parser.add_argument(
        "--preset",
        choices=["zephyr-xen-qemu"],
        help="Fill Docker/QEMU defaults for the reusable Zephyr Xen validation product.",
    )
    parser.add_argument("--cmd")
    parser.add_argument("--timeout-sec", type=float)
    parser.add_argument("--cwd")
    parser.add_argument("--docker-image")
    parser.add_argument("--docker-workdir")
    parser.add_argument("--mount", action="append", default=[])
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--product-dir", type=Path, default=ZEPHYR_XEN_QEMU_PRODUCT)
    parser.add_argument("--qemu-bin")
    parser.add_argument("--dom0-bin")
    parser.add_argument("--domu-bin")
    parser.add_argument("--xen-dtb")
    parser.add_argument("--domu-load-addr")
    parser.add_argument("--xen-static-domu", default="0")
    parser.add_argument("--xen-load-domu-image", default="1")
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        type=lambda value: parse_key_value(value, "--env"),
    )
    parser.add_argument(
        "--expect",
        action="append",
        default=[],
        type=parse_expectation,
    )
    parser.add_argument("--require-source", action="append", default=[])
    parser.add_argument("--xen-switch-at", action="append", default=[], type=float)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--fail-on-timeout", action="store_true")
    parser.add_argument("--no-stop-on-match", action="store_true")
    args = parser.parse_args(argv)
    args.scenario_config = None
    apply_presets(args)
    if args.timeout_sec is None:
        args.timeout_sec = 60.0
    if args.domu_load_addr is None:
        args.domu_load_addr = DEFAULT_DOMU_LOAD_ADDR
    if not args.log_file:
        parser.error("--log-file is required unless --scenario-file supplies it")
    if not args.cmd:
        parser.error("--cmd is required unless --preset supplies it")
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    prepare_rc = prepare_inputs(args)
    if prepare_rc != 0:
        return prepare_rc

    result = run_command(args)
    missing = [item for item in result.expectation_results if not item.found]
    missing_sources = [
        source
        for source in args.require_source
        if result.source_stats.get(source, SourceStats()).bytes == 0
    ]
    failed = bool(missing or missing_sources)
    if args.fail_on_timeout and result.timed_out:
        failed = True
    if (
        result.return_code not in (0, 124)
        and not result.timed_out
        and not result.stopped_on_match
    ):
        failed = True

    for item in result.expectation_results:
        expectation = item.expectation
        status = "found" if item.found else "missing"
        print(f"{status}: {expectation.source}:{expectation.text}")
    for source in args.require_source:
        stats = result.source_stats.get(source, SourceStats())
        status = "found" if stats.bytes > 0 else "missing"
        print(f"{status}: source {source} ({stats.lines} lines, {stats.bytes} bytes)")
    if result.stopped_on_match:
        print("stopped: all requested markers were found")
    print(f"log: {args.log_file}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

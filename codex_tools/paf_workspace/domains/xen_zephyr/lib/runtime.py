#!/usr/bin/env python3
"""Run Xen/QEMU commands and collect domain-oriented logs."""

import argparse
import os
import queue
import re
import select
import signal
import shlex
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, TextIO


XEN_SWITCH_BYTES = b"\x01\x01\x01\x01\x01\x01"
XEN_SWITCH_TEXT = XEN_SWITCH_BYTES.decode("latin1")
XEN_SWITCH_BYTE_DELAY_SEC = 0.05
SERIAL_INPUT_RE = re.compile(r"\(XEN\) \*\*\* Serial input to DOM(\d+)")
HARNESS_DOMAIN_RE = re.compile(r"\[xen-harness\]\[(dom0|domu\d+|xen|host)\]")
XEN_GUEST_PREFIX_RE = re.compile(r"^\(d(\d+)\) ")
HOST_LINE_PREFIXES = (
    "qemu-system-",
)
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


@dataclass(frozen=True)
class StdinEvent:
    at: float
    text: str


@dataclass(frozen=True)
class FollowLog:
    source: str
    path: Path


@dataclass(frozen=True)
class ConsoleSocket:
    source: str
    path: Path


@dataclass(frozen=True)
class QueuedLine:
    source: str | None
    line: str


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
    stdin_events: tuple[StdinEvent, ...] = ()
    stdin_file: Path | None = None
    follow_logs: tuple[FollowLog, ...] = ()
    console_sockets: tuple[ConsoleSocket, ...] = ()
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


def decode_stdin_text(text: str) -> str:
    return text.encode("utf-8").decode("unicode_escape")


def parse_stdin_event(value: str, option: str, *, append_newline: bool = False) -> StdinEvent:
    at_text, sep, text = value.partition(":")
    if not sep or not at_text:
        raise argparse.ArgumentTypeError(f"{option} must use TIME:TEXT")
    try:
        at = float(at_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{option} TIME must be a number") from exc
    if at < 0:
        raise argparse.ArgumentTypeError(f"{option} TIME must be non-negative")

    decoded = decode_stdin_text(text)
    if append_newline:
        decoded += "\n"
    return StdinEvent(at=at, text=decoded)


def parse_xen_switch_event(value: str) -> StdinEvent:
    try:
        at = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--send-xen-switch-at TIME must be a number") from exc
    if at < 0:
        raise argparse.ArgumentTypeError("--send-xen-switch-at TIME must be non-negative")
    return StdinEvent(at=at, text=XEN_SWITCH_TEXT)


def parse_follow_log(value: str) -> FollowLog:
    source, sep, path = value.partition(":")
    if not sep or not source or not path:
        raise argparse.ArgumentTypeError("--follow-log must use SOURCE:PATH")
    return FollowLog(source=source, path=Path(path))


def parse_console_socket(value: str) -> ConsoleSocket:
    source, sep, path = value.partition(":")
    if not sep or not source or not path:
        raise argparse.ArgumentTypeError("--console-socket must use SOURCE:PATH")
    return ConsoleSocket(source=source, path=Path(path))


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


def load_stdin_events(values: object) -> tuple[StdinEvent, ...]:
    if values is None:
        return ()
    if not isinstance(values, list):
        raise ValueError("scenario field 'stdin_events' must be a list")

    events: list[StdinEvent] = []
    for index, value in enumerate(values):
        if not isinstance(value, dict):
            raise ValueError(f"scenario stdin_events[{index}] must be an object")

        at = value.get("at")
        if not isinstance(at, (int, float)) or at < 0:
            raise ValueError(f"scenario stdin_events[{index}].at must be a non-negative number")

        event_type = optional_string(value, "type") or "text"
        if event_type == "xen-switch":
            text = XEN_SWITCH_TEXT
        elif event_type == "line":
            text = decode_stdin_text(require_string(value, "text")) + "\n"
        elif event_type == "text":
            text = decode_stdin_text(require_string(value, "text"))
        else:
            raise ValueError(
                f"scenario stdin_events[{index}].type must be text, line, or xen-switch"
            )
        events.append(StdinEvent(at=float(at), text=text))
    return tuple(events)


def load_follow_logs(values: object) -> tuple[FollowLog, ...]:
    if values is None:
        return ()
    if not isinstance(values, list):
        raise ValueError("scenario field 'follow_logs' must be a list")

    logs: list[FollowLog] = []
    for index, value in enumerate(values):
        if not isinstance(value, dict):
            raise ValueError(f"scenario follow_logs[{index}] must be an object")
        logs.append(
            FollowLog(
                source=require_string(value, "source"),
                path=Path(require_string(value, "path")),
            )
        )
    return tuple(logs)


def load_console_sockets(values: object) -> tuple[ConsoleSocket, ...]:
    if values is None:
        return ()
    if not isinstance(values, list):
        raise ValueError("scenario field 'console_sockets' must be a list")

    sockets: list[ConsoleSocket] = []
    for index, value in enumerate(values):
        if not isinstance(value, dict):
            raise ValueError(f"scenario console_sockets[{index}] must be an object")
        sockets.append(
            ConsoleSocket(
                source=require_string(value, "source"),
                path=Path(require_string(value, "path")),
            )
        )
    return tuple(sockets)


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


def load_scenario_data(data: object) -> Scenario:
    if not isinstance(data, dict):
        raise ValueError("scenario must be an object")

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
        stdin_events=load_stdin_events(data.get("stdin_events")),
        stdin_file=Path(stdin_file) if (stdin_file := optional_string(data, "stdin_file")) else None,
        follow_logs=load_follow_logs(data.get("follow_logs")),
        console_sockets=load_console_sockets(data.get("console_sockets")),
        domu_build=load_zephyr_build(data.get("domu_build")),
        expected_abi=load_abi_expectation(data.get("expected_abi")),
        domu_load_addr=optional_string(data, "domu_load_addr") or DEFAULT_DOMU_LOAD_ADDR,
        env=load_env(data.get("env")),
    )


def args_from_scenario(
    scenario: Scenario,
    *,
    root: Path,
    product_dir: Path | None = None,
    log_file: Path | None = None,
    command: str | None = None,
    container_alias: str | None = None,
    container_workdir: str | None = None,
    qemu_bin: str | None = None,
    xen_dtb: str | None = None,
    fail_on_timeout: bool = False,
    no_stop_on_match: bool = False,
) -> argparse.Namespace:
    args = argparse.Namespace(
        scenario_file=None,
        scenario_config=scenario,
        log_file=log_file or (Path(scenario.log_file) if scenario.log_file else None),
        preset=scenario.preset,
        cmd=command,
        timeout_sec=scenario.timeout_sec,
        cwd=None,
        container_alias=container_alias,
        container_workdir=container_workdir or "/home/builder/workspace",
        launch_command=None,
        workspace_root=root,
        product_dir=product_dir or ZEPHYR_XEN_QEMU_PRODUCT,
        qemu_bin=qemu_bin,
        dom0_bin=scenario.dom0_bin,
        domu_bin=scenario.domu_bin,
        xen_dtb=xen_dtb,
        domu_load_addr=scenario.domu_load_addr,
        xen_static_domu="0",
        xen_load_domu_image="1",
        env=[],
        expect=[],
        require_source=[],
        stdin_event=[],
        follow_log=[],
        console_socket=[],
        stdin_file=scenario.stdin_file,
        xen_switch_at=[],
        skip_build=False,
        skip_preflight=False,
        fail_on_timeout=fail_on_timeout,
        no_stop_on_match=no_stop_on_match,
    )
    append_expectations(args, scenario.expect)
    args.require_source.extend(scenario.require_source)
    append_stdin_events(args, scenario.stdin_events)
    append_follow_logs(args, scenario.follow_logs)
    append_console_sockets(args, scenario.console_sockets)
    apply_presets(args)
    if args.timeout_sec is None:
        args.timeout_sec = 60.0
    if args.log_file is None:
        raise ValueError("harness scenario requires log_file")
    if not args.cmd:
        raise ValueError("harness scenario requires command or preset")
    return args


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


def append_stdin_events(args: argparse.Namespace, events: tuple[StdinEvent, ...]) -> None:
    args.stdin_event.extend(events)


def append_follow_logs(args: argparse.Namespace, logs: tuple[FollowLog, ...]) -> None:
    args.follow_log.extend(logs)


def append_console_sockets(args: argparse.Namespace, sockets: tuple[ConsoleSocket, ...]) -> None:
    args.console_socket.extend(sockets)


def workspace_root(args: argparse.Namespace) -> Path:
    if args.workspace_root:
        return args.workspace_root.resolve()
    return Path.cwd().resolve()


def resolve_workspace_path(path_text: str, root: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path.resolve()
    return (root / path).resolve()


def container_path(path_text: str, root: Path, product_dir: Path, container_workdir: str) -> str:
    path = resolve_workspace_path(path_text, root)
    container_root = Path(container_workdir)

    try:
        return str(container_root / product_dir.relative_to(root) / path.relative_to(product_dir))
    except ValueError:
        pass

    try:
        return str(container_root / path.relative_to(root))
    except ValueError:
        return path_text


def apply_scenario_env(args: argparse.Namespace) -> None:
    scenario = getattr(args, "scenario_config", None)
    if scenario is None:
        return

    for key, value in scenario.env:
        append_env(args, key, value)


def apply_zephyr_xen_qemu_preset(args: argparse.Namespace) -> None:
    root = workspace_root(args)
    product_dir = (root / args.product_dir).resolve()
    container_workdir = args.container_workdir or "/home/builder/workspace"
    container_product_dir = container_path(str(product_dir), root, product_dir, container_workdir)

    if not args.cmd:
        args.cmd = (
            f"cd {shlex.quote(container_product_dir)} && "
            "bash ./scripts/gen-xen-dtb.sh /tmp/xen-qemu-harness.yaml >/dev/null && "
            "./run/run-qemu.sh"
        )

    append_env(args, "QEMU_BIN", args.qemu_bin or ZEPHYR_XEN_QEMU_QEMU_BIN)
    append_env(args, "XEN_STATIC_DOMU", args.xen_static_domu)
    append_env(args, "XEN_LOAD_DOMU_IMAGE", args.xen_load_domu_image)
    append_env(args, "DOMU_LOAD_ADDR", args.domu_load_addr)

    if args.dom0_bin:
        append_env(args, "DOM0_BIN", container_path(args.dom0_bin, root, product_dir, container_workdir))
    if args.domu_bin:
        append_env(args, "DOMU_BIN", container_path(args.domu_bin, root, product_dir, container_workdir))
    if args.xen_dtb:
        append_env(args, "XEN_DTB", container_path(args.xen_dtb, root, product_dir, container_workdir))


def apply_presets(args: argparse.Namespace) -> None:
    if args.preset == "zephyr-xen-qemu":
        apply_zephyr_xen_qemu_preset(args)
    apply_scenario_env(args)


def run_zephyr_build(build: ZephyrBuild, root: Path) -> int:
    print(
        "build: Zephyr builds are executed by the environments PAF domain; "
        "set skip_build after the PAF task completes",
        file=sys.stderr,
    )
    return 2


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


def command_with_exports(args: argparse.Namespace) -> str:
    exports = []
    for key, value in args.env:
        exports.append(f"export {key}={shlex.quote(value)}")
    exports.append(args.cmd)
    return "\n".join(exports)


def build_command(args: argparse.Namespace) -> list[str] | str:
    if args.launch_command is not None:
        return args.launch_command
    return command_with_exports(args)


def shell_command(args: argparse.Namespace) -> str:
    command = build_command(args)
    if isinstance(command, list):
        return shlex.join(command)
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
    stdin: TextIO,
    events: list[StdinEvent],
    timeout_sec: float,
) -> None:
    started = time.monotonic()
    for event in sorted(events, key=lambda item: item.at):
        delay = started + event.at - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        try:
            if event.text == XEN_SWITCH_TEXT:
                for char in event.text:
                    stdin.write(char)
                    stdin.flush()
                    time.sleep(XEN_SWITCH_BYTE_DELAY_SEC)
            else:
                stdin.write(event.text)
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


def write_stdin_file_events(
    path: Path,
    events: list[StdinEvent],
    timeout_sec: float,
) -> None:
    deadline = time.monotonic() + timeout_sec
    while True:
        try:
            with path.open("w", buffering=1, errors="replace") as output:
                write_stdin_events(output, events, timeout_sec)
                return
        except FileNotFoundError:
            if time.monotonic() >= deadline:
                return
            time.sleep(0.05)


def send_stdin_event_to_socket(sock: socket.socket, event: StdinEvent) -> None:
    if event.text == XEN_SWITCH_TEXT:
        for char in event.text:
            sock.sendall(char.encode("latin1"))
            time.sleep(XEN_SWITCH_BYTE_DELAY_SEC)
        return
    sock.sendall(event.text.encode())


def enqueue_output(stdout: Iterable[str], lines: queue.Queue[QueuedLine]) -> None:
    for line in stdout:
        lines.put(QueuedLine(source=None, line=line))


def enqueue_follow_log(
    source: str,
    path: Path,
    lines: queue.Queue[QueuedLine],
    stop_event: threading.Event,
) -> None:
    offset = 0
    while not stop_event.is_set():
        try:
            with path.open("r", errors="replace") as input_file:
                input_file.seek(offset)
                while not stop_event.is_set():
                    line = input_file.readline()
                    if line:
                        offset = input_file.tell()
                        lines.put(QueuedLine(source=source, line=line))
                        continue
                    time.sleep(0.05)
        except FileNotFoundError:
            time.sleep(0.05)


def enqueue_console_socket(
    source: str,
    path: Path,
    events: list[StdinEvent],
    timeout_sec: float,
    lines: queue.Queue[QueuedLine],
    stop_event: threading.Event,
) -> None:
    deadline = time.monotonic() + timeout_sec
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        while not stop_event.is_set():
            try:
                sock.connect(str(path))
                break
            except (FileNotFoundError, ConnectionRefusedError):
                if time.monotonic() >= deadline:
                    return
                time.sleep(0.05)
        sock.setblocking(False)

        started = time.monotonic()
        pending_events = sorted(events, key=lambda item: item.at)
        event_index = 0
        pending = ""
        while not stop_event.is_set() and time.monotonic() < deadline:
            now = time.monotonic()
            while event_index < len(pending_events) and started + pending_events[event_index].at <= now:
                send_stdin_event_to_socket(sock, pending_events[event_index])
                event_index += 1

            readable, _, _ = select.select([sock], [], [], 0.05)
            if not readable:
                continue

            chunk = sock.recv(4096)
            if not chunk:
                break
            pending += chunk.decode(errors="replace")
            while "\n" in pending:
                line, pending = pending.split("\n", 1)
                lines.put(QueuedLine(source=source, line=f"{line}\n"))

        if pending:
            lines.put(QueuedLine(source=source, line=pending))
    finally:
        sock.close()


def terminate_process(process: subprocess.Popen[str]) -> int:
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
    shell = isinstance(command, str)
    cwd = args.cwd if shell else None
    timed_out = False
    stopped_on_match = False
    active_guest: str | None = None
    source_stats: dict[str, SourceStats] = {}
    expectation_results = [ExpectationResult(expectation) for expectation in args.expect]
    line_queue: queue.Queue[QueuedLine] = queue.Queue()
    stop_event = threading.Event()
    deadline = time.monotonic() + args.timeout_sec

    args.log_file.parent.mkdir(parents=True, exist_ok=True)
    with args.log_file.open("w", errors="replace") as output:
        auxiliary_threads: list[threading.Thread] = []
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
        stdin_thread = None
        if args.console_socket:
            process.stdin.close()
        else:
            if args.stdin_file is not None:
                stdin_path = args.stdin_file
                if not stdin_path.is_absolute():
                    stdin_path = workspace_root(args) / stdin_path
                stdin_thread = threading.Thread(
                    target=write_stdin_file_events,
                    args=(stdin_path, args.stdin_event, args.timeout_sec),
                    daemon=True,
                )
            else:
                stdin_thread = threading.Thread(
                    target=write_stdin_events,
                    args=(process.stdin, args.stdin_event, args.timeout_sec),
                    daemon=True,
                )
            stdin_thread.start()
        stdout_thread = threading.Thread(
            target=enqueue_output,
            args=(process.stdout, line_queue),
            daemon=True,
        )
        stdout_thread.start()
        for console_socket in args.console_socket:
            socket_path = console_socket.path
            socket_thread = threading.Thread(
                target=enqueue_console_socket,
                args=(
                    console_socket.source,
                    socket_path,
                    args.stdin_event,
                    args.timeout_sec,
                    line_queue,
                    stop_event,
                ),
                daemon=True,
            )
            socket_thread.start()
            auxiliary_threads.append(socket_thread)
        for follow_log in args.follow_log:
            follow_path = follow_log.path
            if not follow_path.is_absolute():
                follow_path = workspace_root(args) / follow_path
            follow_thread = threading.Thread(
                target=enqueue_follow_log,
                args=(follow_log.source, follow_path, line_queue, stop_event),
                daemon=True,
            )
            follow_thread.start()
            auxiliary_threads.append(follow_thread)

        while True:
            try:
                queued = line_queue.get(timeout=0.1)
            except queue.Empty:
                if process.poll() is not None and line_queue.empty():
                    return_code = process.returncode
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    return_code = terminate_process(process)
                    break
                continue

            line = queued.line
            if queued.source is None:
                source, active_guest = source_for_line(line, active_guest)
            else:
                source = queued.source
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

        if stdin_thread is not None:
            stdin_thread.join(timeout=1)
        stdout_thread.join(timeout=1)
        stop_event.set()
        for auxiliary_thread in auxiliary_threads:
            auxiliary_thread.join(timeout=1)

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


def evaluate_result(args: argparse.Namespace, result: RunResult) -> int:
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


def run_prepared_args(args: argparse.Namespace) -> int:
    return evaluate_result(args, run_command(args))


def run_harness_args(args: argparse.Namespace) -> int:
    prepare_rc = prepare_inputs(args)
    if prepare_rc != 0:
        return prepare_rc
    return run_prepared_args(args)

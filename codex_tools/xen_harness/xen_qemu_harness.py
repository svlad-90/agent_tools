#!/usr/bin/env python3
"""Run Xen/QEMU commands and collect domain-oriented logs."""

from __future__ import annotations

import argparse
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
SERIAL_INPUT_RE = re.compile(r"\(XEN\) \*\*\* Serial input to DOM(\d+)")
HARNESS_DOMAIN_RE = re.compile(r"\[xen-harness\]\[(dom0|domu\d+|xen|host)\]")
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


def append_env(args: argparse.Namespace, key: str, value: str | None) -> None:
    if value is None:
        return
    args.env = [item for item in args.env if item[0] != key]
    args.env.append((key, value))


def workspace_root(args: argparse.Namespace) -> Path:
    if args.workspace_root:
        return args.workspace_root.resolve()
    return Path.cwd().resolve()


def docker_path(path_text: str, root: Path, product_dir: Path) -> str:
    path = Path(path_text)
    if not path.is_absolute():
        return path_text

    try:
        return str(Path("/home/builder/workspace") / path.relative_to(product_dir))
    except ValueError:
        pass

    try:
        return str(Path("/workspace") / path.relative_to(root))
    except ValueError:
        return path_text


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
    if args.preset == "zephyr-xen-qemu":
        apply_zephyr_xen_qemu_preset(args)


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
            stdin.write(XEN_SWITCH_BYTES)
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
    if line.startswith("(XEN)"):
        return "xen", next_guest
    if line.startswith(HOST_LINE_PREFIXES):
        return "host", next_guest
    if active_guest:
        return active_guest, next_guest
    return "unknown", next_guest


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-file", required=True, type=Path)
    parser.add_argument(
        "--preset",
        choices=["zephyr-xen-qemu"],
        help="Fill Docker/QEMU defaults for the reusable Zephyr Xen validation product.",
    )
    parser.add_argument("--cmd")
    parser.add_argument("--timeout-sec", type=float, default=60.0)
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
    parser.add_argument("--domu-load-addr", default="0x59000000")
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
    parser.add_argument("--fail-on-timeout", action="store_true")
    parser.add_argument("--no-stop-on-match", action="store_true")
    args = parser.parse_args(argv)
    apply_presets(args)
    if not args.cmd:
        parser.error("--cmd is required unless --preset supplies it")
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
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

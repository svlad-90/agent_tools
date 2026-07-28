#!/usr/bin/env python3
"""Run Xen/QEMU commands and collect domain-oriented logs."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path


XEN_SWITCH_BYTES = b"\x01\x01\x01\x01\x01\x01"
SERIAL_INPUT_RE = re.compile(r"\(XEN\) \*\*\* Serial input to DOM(\d+)")


@dataclass(frozen=True)
class Expectation:
    source: str
    text: str


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


def run_command(args: argparse.Namespace, raw_log: Path) -> tuple[int, bool]:
    command = build_command(args)
    shell = not args.docker_image
    cwd = args.cwd if not args.docker_image else None
    timed_out = False

    with raw_log.open("wb") as output:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            shell=shell,
            stdin=subprocess.PIPE,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        assert process.stdin is not None
        stdin_thread = threading.Thread(
            target=write_stdin_events,
            args=(process.stdin, args.xen_switch_at, args.timeout_sec),
            daemon=True,
        )
        stdin_thread.start()
        try:
            return_code = process.wait(timeout=args.timeout_sec)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            try:
                return_code = process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                return_code = process.wait()
        stdin_thread.join(timeout=1)

    if timed_out:
        return 124, timed_out
    return return_code, timed_out


def source_for_line(line: str, active_guest: str | None) -> tuple[str, str | None]:
    match = SERIAL_INPUT_RE.search(line)
    next_guest = active_guest
    if match:
        domain_id = match.group(1)
        next_guest = "dom0" if domain_id == "0" else f"domu{domain_id}"

    if line.startswith("(XEN)"):
        return "xen", next_guest
    if active_guest:
        return active_guest, next_guest
    return "unknown", next_guest


def split_raw_log(raw_log: Path, out_dir: Path) -> dict[str, str]:
    logs: dict[str, list[str]] = {
        "raw": raw_log.read_text(errors="replace").splitlines(keepends=True),
        "xen": [],
        "dom0": [],
        "unknown": [],
        "combined": [],
    }
    active_guest: str | None = None

    for line in logs["raw"]:
        source, active_guest = source_for_line(line, active_guest)
        logs.setdefault(source, []).append(line)
        logs["combined"].append(f"[{source}] {line}")

    written = {}
    for source, lines in logs.items():
        path = out_dir / f"{source}.log"
        path.write_text("".join(lines), errors="replace")
        written[source] = str(path)
    return written


def copy_extra_sources(
    sources: list[tuple[str, str]],
    out_dir: Path,
    logs: dict[str, str],
) -> None:
    for name, source_path in sources:
        destination = out_dir / f"{name}.log"
        shutil.copyfile(source_path, destination)
        logs[name] = str(destination)


def check_expectations(
    expectations: list[Expectation],
    logs: dict[str, str],
) -> list[dict[str, object]]:
    results = []
    for expectation in expectations:
        path = logs.get(expectation.source)
        text = ""
        if path:
            text = Path(path).read_text(errors="replace")
        results.append(
            {
                "source": expectation.source,
                "text": expectation.text,
                "found": expectation.text in text,
                "path": path,
            }
        )
    return results


def write_summary(
    args: argparse.Namespace,
    logs: dict[str, str],
    return_code: int,
    timed_out: bool,
    expectation_results: list[dict[str, object]],
) -> None:
    summary = {
        "command": args.cmd,
        "docker_image": args.docker_image,
        "return_code": return_code,
        "timed_out": timed_out,
        "timeout_sec": args.timeout_sec,
        "logs": logs,
        "expectations": expectation_results,
    }
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--cmd", required=True)
    parser.add_argument("--timeout-sec", type=float, default=60.0)
    parser.add_argument("--cwd")
    parser.add_argument("--docker-image")
    parser.add_argument("--docker-workdir")
    parser.add_argument("--mount", action="append", default=[])
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        type=lambda value: parse_key_value(value, "--env"),
    )
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        type=lambda value: parse_key_value(value, "--source"),
    )
    parser.add_argument(
        "--expect",
        action="append",
        default=[],
        type=parse_expectation,
    )
    parser.add_argument("--xen-switch-at", action="append", default=[], type=float)
    parser.add_argument("--fail-on-timeout", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    raw_log = args.out_dir / "raw.log"

    return_code, timed_out = run_command(args, raw_log)
    logs = split_raw_log(raw_log, args.out_dir)
    copy_extra_sources(args.source, args.out_dir, logs)
    expectation_results = check_expectations(args.expect, logs)
    write_summary(args, logs, return_code, timed_out, expectation_results)

    missing = [item for item in expectation_results if not item["found"]]
    failed = bool(missing)
    if args.fail_on_timeout and timed_out:
        failed = True
    if return_code not in (0, 124) and not timed_out:
        failed = True

    for item in expectation_results:
        status = "found" if item["found"] else "missing"
        print(f"{status}: {item['source']}:{item['text']}")
    print(f"raw log: {logs['raw']}")
    print(f"combined log: {logs['combined']}")
    print(f"summary: {args.out_dir / 'summary.json'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

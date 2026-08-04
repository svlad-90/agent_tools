"""Helpers for Yocto and BitBake diagnostics."""

from __future__ import annotations

import argparse
import shlex
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


DEFAULT_GRAPH_FILES = (
    "task-depends.dot",
    "pn-buildlist",
    "recipe-depends.dot",
    "package-depends.dot",
)


def quote_words(value: str) -> str:
    words = shlex.split(value)
    if not words:
        raise ValueError("empty word list")
    return " ".join(shlex.quote(word) for word in words)


def safe_label(value: str) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in value)


@dataclass(frozen=True)
class YoctoInvocation:
    yocto_dir: str
    build_dir: str = "build-xen-qemu-421"
    init_script: str = "poky/oe-init-build-env"


@dataclass(frozen=True)
class GraphCopy:
    output_dir: str
    label: str = "bitbake-graph"
    files: tuple[str, ...] = DEFAULT_GRAPH_FILES


def graph_copy_body(copy: GraphCopy) -> str:
    quoted_output_dir = shlex.quote(copy.output_dir)
    quoted_label = shlex.quote(safe_label(copy.label))
    quoted_files = " ".join(shlex.quote(item) for item in copy.files)
    return "\n".join(
        (
            'if [ "${rc}" -eq 0 ]; then',
            f"  mkdir -p {quoted_output_dir}",
            f"  for graph_file in {quoted_files}; do",
            '    if [ -f "${graph_file}" ]; then',
            f"      cp \"${{graph_file}}\" {quoted_output_dir}/{quoted_label}-\"${{graph_file}}\"",
            "    fi",
            "  done",
            "fi",
        )
    )


def bitbake_shell_command(
    invocation: YoctoInvocation,
    bitbake_args: str,
    *,
    graph_copy: GraphCopy | None = None,
) -> str:
    extra_body = graph_copy_body(graph_copy) if graph_copy else ""
    body = "\n".join(
        line
        for line in (
            "set -uo pipefail",
            f"cd {shlex.quote(invocation.yocto_dir)}",
            "set +u",
            f"source {shlex.quote(invocation.init_script)} {shlex.quote(invocation.build_dir)}",
            "set -u",
            'server_timeout="${YOCTO_BITBAKE_SERVER_TIMEOUT_SEC:-10}"',
            'BB_SERVER_TIMEOUT="${server_timeout}" bitbake -T "${server_timeout}" -m >/dev/null 2>&1 || true',
            "rc=0",
            f'BB_SERVER_TIMEOUT="${{server_timeout}}" bitbake -T "${{server_timeout}}" {bitbake_args} || rc=$?',
            extra_body,
            'BB_SERVER_TIMEOUT="${server_timeout}" bitbake -T "${server_timeout}" -m >/dev/null 2>&1 || true',
            'exit "${rc}"',
        )
        if line
    )
    return f"bash -lc {shlex.quote(body)}"


def read_buildlist(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    ]


def iter_dot_edges(path: Path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "->" not in line:
            continue
        left, _, right = line.partition("->")
        source = left.strip().strip('"')
        target = right.split("[", 1)[0].strip().rstrip(";").strip('"')
        if source and target:
            yield source, target


def analyze_graph_files(prefix: Path) -> str:
    files = {
        "buildlist": prefix.with_name(prefix.name + "-pn-buildlist"),
        "task_depends": prefix.with_name(prefix.name + "-task-depends.dot"),
        "recipe_depends": prefix.with_name(prefix.name + "-recipe-depends.dot"),
        "package_depends": prefix.with_name(prefix.name + "-package-depends.dot"),
    }
    buildlist = read_buildlist(files["buildlist"])
    sections = [
        "# Yocto Graph Summary",
        "",
        f"- prefix: `{prefix}`",
        f"- recipes in pn-buildlist: {len(buildlist)}",
    ]

    if buildlist:
        sections.append("- first buildlist entries: " + ", ".join(f"`{item}`" for item in buildlist[:20]))

    for name in ("task_depends", "recipe_depends", "package_depends"):
        edges = list(iter_dot_edges(files[name]))
        inbound = Counter(target for _, target in edges)
        outbound = Counter(source for source, _ in edges)
        sections.extend(
            [
                "",
                f"## {name.replace('_', ' ').title()}",
                "",
                f"- file: `{files[name]}`",
                f"- edges: {len(edges)}",
                f"- nodes with outgoing edges: {len(outbound)}",
                f"- nodes with incoming edges: {len(inbound)}",
            ]
        )
        if inbound:
            top_inbound = ", ".join(f"`{node}` ({count})" for node, count in inbound.most_common(10))
            sections.append(f"- most depended-on nodes: {top_inbound}")
        if outbound:
            top_outbound = ", ".join(f"`{node}` ({count})" for node, count in outbound.most_common(10))
            sections.append(f"- nodes with most dependencies: {top_outbound}")

    return "\n".join(sections) + "\n"


def build_command(args: argparse.Namespace) -> int:
    graph_copy = None
    if args.graph_output_dir:
        files = tuple(args.graph_files or DEFAULT_GRAPH_FILES)
        graph_copy = GraphCopy(args.graph_output_dir, args.graph_label, files)
    invocation = YoctoInvocation(args.yocto_dir, args.build_dir, args.init_script)
    print(bitbake_shell_command(invocation, quote_words(args.bitbake_args), graph_copy=graph_copy))
    return 0


def analyze_graph_command(args: argparse.Namespace) -> int:
    print(analyze_graph_files(Path(args.prefix)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Yocto diagnostic helpers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    command = subparsers.add_parser("command", help="Build a BitBake shell command.")
    command.add_argument("--yocto-dir", required=True)
    command.add_argument("--build-dir", default="build-xen-qemu-421")
    command.add_argument("--init-script", default="poky/oe-init-build-env")
    command.add_argument("--graph-output-dir", default="")
    command.add_argument("--graph-label", default="bitbake-graph")
    command.add_argument("--graph-files", nargs="*")
    command.add_argument("bitbake_args")
    command.set_defaults(handler=build_command)

    graph = subparsers.add_parser("analyze-graph", help="Summarize BitBake graph files by prefix.")
    graph.add_argument("prefix")
    graph.set_defaults(handler=analyze_graph_command)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.handler(args) or 0)

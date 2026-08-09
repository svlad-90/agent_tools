from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .comments_compose import compose_comments_payload_with_diagnostics
from .comments_template import build_comments_template
from .core import compact_help, generate_report
from .diff_source import load_diff_source
from .models import DiffReportError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a GitHub-style HTML diff report with review comments.",
    )
    parser.add_argument("--repo", help="Git repository path. Required unless --diff-file is used.")
    parser.add_argument(
        "--range",
        dest="rev_range",
        default="HEAD^..HEAD",
        help="Git revision range to diff, for example HEAD^..HEAD or BASE..HEAD.",
    )
    parser.add_argument("--diff-file", help="Read unified git diff from this file instead of running git.")
    parser.add_argument("--comments", help="JSON file with file-level and inline review comments.")
    parser.add_argument("--init-comments", help="Write starter comments JSON from the diff and exit.")
    parser.add_argument("--findings", help="JSON file with draft findings to compose into comments JSON.")
    parser.add_argument("--output-comments", help="Write composed comments JSON and exit.")
    parser.add_argument("--compose-report", help="Write findings compose diagnostics JSON.")
    parser.add_argument("--output", help="HTML report output path.")
    parser.add_argument("--title", default="PR Diff Review", help="Report title.")
    parser.add_argument("--context", type=int, default=80, help="Git diff context lines.")
    parser.add_argument(
        "--refresh-targets",
        action="store_true",
        help=(
            "Refresh target anchors in the same-basename comments JSON before "
            "rendering self-contained HTML."
        ),
    )
    parser.add_argument(
        "--display-label",
        help="Human-facing diff source label, for example 'Commit 01'.",
    )
    parser.add_argument("--help-compact", action="store_true", help="Print compact CLI synopsis.")

    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.help_compact:
        print(compact_help())
        return 0
    if args.findings and not args.output_comments:
        parser.error("--output-comments is required when --findings is used")
    if args.output_comments and not args.findings:
        parser.error("--findings is required when --output-comments is used")
    if not args.output and not args.init_comments and not args.output_comments:
        parser.error(
            "--output is required unless --help-compact, --init-comments, or --output-comments is used"
        )

    try:
        output = _resolve_path(args.output) if args.output else None
        repo = _resolve_path(args.repo) if args.repo else None
        diff_file = _resolve_path(args.diff_file) if args.diff_file else None
        comments_file = _resolve_path(args.comments) if args.comments else None
        init_comments = _resolve_path(args.init_comments) if args.init_comments else None
        findings_file = _resolve_path(args.findings) if args.findings else None
        output_comments = _resolve_path(args.output_comments) if args.output_comments else None
        compose_report = _resolve_path(args.compose_report) if args.compose_report else None
        if init_comments is not None:
            source = load_diff_source(
                repo,
                args.rev_range,
                diff_file,
                args.context,
                args.display_label,
            )
            init_comments.parent.mkdir(parents=True, exist_ok=True)
            init_comments.write_text(
                json.dumps(build_comments_template(source.diff_text), indent=2) + "\n",
                encoding="utf-8",
            )
            print(str(init_comments))
            return 0
        if output_comments is not None:
            source = load_diff_source(
                repo,
                args.rev_range,
                diff_file,
                args.context,
                args.display_label,
            )
            if findings_file is None:
                parser.error("--findings is required when --output-comments is used")
            findings = json.loads(findings_file.read_text(encoding="utf-8"))
            composed, diagnostics = compose_comments_payload_with_diagnostics(
                source.diff_text,
                findings,
            )
            output_comments.parent.mkdir(parents=True, exist_ok=True)
            output_comments.write_text(
                json.dumps(
                    composed,
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            print(str(output_comments))
            if compose_report is not None:
                compose_report.parent.mkdir(parents=True, exist_ok=True)
                compose_report.write_text(
                    json.dumps({"diagnostics": diagnostics}, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                print(str(compose_report))
            if diagnostics:
                print(f"compose-findings: diagnostics={len(diagnostics)}", file=sys.stderr)
                return 1
            if output is not None:
                generate_report(
                    output_path=output,
                    title=args.title,
                    repo_path=repo,
                    rev_range=args.rev_range,
                    diff_file=diff_file,
                    comments_file=output_comments,
                    context=args.context,
                    display_label=args.display_label,
                    refresh_targets=args.refresh_targets,
                )
                print(str(output))
            return 0
        if output is None:
            parser.error(
                "--output is required unless --help-compact, --init-comments, or --output-comments is used"
            )
        generate_report(
            output_path=output,
            title=args.title,
            repo_path=repo,
            rev_range=args.rev_range,
            diff_file=diff_file,
            comments_file=comments_file,
            context=args.context,
            display_label=args.display_label,
            refresh_targets=args.refresh_targets,
        )
        print(str(output))
        return 0
    except (DiffReportError, ValueError, OSError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 1


def _resolve_path(path_text: str | None) -> Path | None:
    if path_text is None:
        return None
    path = Path(path_text)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path

from __future__ import annotations

from .core import compact_help, generate_report, generate_report_json
from .models import DiffReportError


def main(argv: list[str] | None = None) -> int:
    from .cli import main as cli_main

    return cli_main(argv)


__all__ = [
    "DiffReportError",
    "compact_help",
    "generate_report",
    "generate_report_json",
    "main",
]

"""Command-line entry point for Yocto diagnostics."""

from __future__ import annotations

from agent_tools.tools.yocto_diag import main


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from .src.commands import codex_main


def main() -> int:
    return codex_main()


if __name__ == "__main__":
    raise SystemExit(main())

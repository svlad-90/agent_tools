from __future__ import annotations

from .src.commands import claude_main


def main() -> int:
    return claude_main()


if __name__ == "__main__":
    raise SystemExit(main())

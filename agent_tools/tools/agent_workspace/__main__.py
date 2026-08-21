from __future__ import annotations

import argparse
from collections.abc import Callable
import importlib
import sys


UI_MODULES = {
    "gtk": "gtk_ui",
    "web": "web_ui",
    "tk": "ui",
}
AUTO_UI_ORDER = ("gtk", "web", "tk")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open the local workspace task dashboard.")
    parser.add_argument(
        "--ui",
        choices=("auto", *UI_MODULES),
        default="auto",
        help="UI backend. Default: auto.",
    )
    args, remaining = parser.parse_known_args(argv)
    choices = AUTO_UI_ORDER if args.ui == "auto" else (args.ui,)
    errors: list[str] = []
    for ui_name in choices:
        try:
            ui_main = _load_ui_main(ui_name)
        except (ImportError, ValueError) as exc:
            errors.append(f"{ui_name}: {exc}")
            continue
        return int(ui_main(remaining) or 0)
    print("Agent Workspace UI is unavailable.", file=sys.stderr)
    for error in errors:
        print(f"  {error}", file=sys.stderr)
    return 1


def _load_ui_main(ui_name: str) -> Callable[[list[str] | None], int]:
    module_name = UI_MODULES[ui_name]
    module = importlib.import_module(f"{__package__}.{module_name}")
    ui_main = getattr(module, "main")
    if not callable(ui_main):
        raise ImportError(f"{module_name}.main is not callable")
    return ui_main


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations


try:
    from .gtk_ui import main
except (ImportError, ValueError):
    from .ui import main


if __name__ == "__main__":
    raise SystemExit(main())

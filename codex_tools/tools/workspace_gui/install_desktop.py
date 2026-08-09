from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


def main() -> int:
    workspace = Path(__file__).resolve().parents[3]
    icon_source = Path(__file__).with_name("assets") / "workspace-gui.svg"
    desktop_source = workspace / "workspace-gui.desktop"
    icon_target = Path.home() / ".local/share/icons/hicolor/scalable/apps/workspace-gui.svg"
    desktop_target = Path.home() / ".local/share/applications/workspace-gui.desktop"

    icon_target.parent.mkdir(parents=True, exist_ok=True)
    desktop_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(icon_source, icon_target)
    shutil.copy2(desktop_source, desktop_target)

    _run_optional(["gtk-update-icon-cache", "-f", str(icon_target.parents[2])])
    _run_optional(["update-desktop-database", str(desktop_target.parent)])
    return 0


def _run_optional(command: list[str]) -> None:
    if shutil.which(command[0]) is None:
        return
    subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    raise SystemExit(main())

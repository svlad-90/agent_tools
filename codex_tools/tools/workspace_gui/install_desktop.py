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
    _install_png_icons(icon_source)

    _run_optional(["gtk-update-icon-cache", "-f", str(icon_target.parents[2])])
    _run_optional(["update-desktop-database", str(desktop_target.parent)])
    return 0


def _install_png_icons(icon_source: Path) -> None:
    convert = shutil.which("convert")
    if convert is None:
        return
    for size in (32, 48, 64, 128, 256):
        target = Path.home() / f".local/share/icons/hicolor/{size}x{size}/apps/workspace-gui.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [convert, "-background", "none", str(icon_source), "-resize", f"{size}x{size}", str(target)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _run_optional(command: list[str]) -> None:
    if shutil.which(command[0]) is None:
        return
    subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    raise SystemExit(main())

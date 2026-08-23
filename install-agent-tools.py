#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import venv


WORKSPACE_ROOT = Path(__file__).resolve().parent
AGENT_TOOLS_ROOT = WORKSPACE_ROOT / "agent_tools"
DEFAULT_VENV = AGENT_TOOLS_ROOT / ".venv"
REQUIREMENTS_ROOT = AGENT_TOOLS_ROOT / "tools" / "requirements"

APT_GUI_PACKAGES = (
    "python3-gi",
    "python3-gi-cairo",
    "gir1.2-gtk-3.0",
    "gir1.2-vte-2.91",
    "desktop-file-utils",
)
DNF_GUI_PACKAGES = (
    "python3-gobject",
    "gtk3",
    "vte291",
    "desktop-file-utils",
)
PACMAN_GUI_PACKAGES = (
    "python-gobject",
    "gtk3",
    "vte3",
    "desktop-file-utils",
)
BREW_GUI_PACKAGES = (
    "pygobject3",
    "gtk+3",
)
ZYPPER_GUI_PACKAGES = (
    "gtk3",
    "typelib-1_0-Gtk-3_0",
    "typelib-1_0-Vte-2_91",
    "desktop-file-utils",
)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not AGENT_TOOLS_ROOT.is_dir():
        print(f"agent_tools directory not found: {AGENT_TOOLS_ROOT}", file=sys.stderr)
        return 1

    if args.gui and not args.skip_system_deps:
        _install_gui_system_dependencies(args)

    python = _ensure_venv(args)
    _install_python_dependencies(python, args)
    if not args.no_launcher:
        _write_launcher(python, args)
    if not args.no_desktop and platform.system() == "Linux":
        _install_desktop_entry(python, args)
    if not args.no_skills:
        _sync_agent_skills(python, args)
    if not args.no_validate:
        _validate_installation(python, args)

    print("Agent tools installation complete.")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install Agent Workspace and workspace-local agent tools.",
    )
    parser.add_argument(
        "--venv",
        type=Path,
        default=DEFAULT_VENV,
        help=f"Virtual environment path. Default: {DEFAULT_VENV}",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Install developer/test Python dependencies.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Also install GTK/VTE packages for the legacy GTK UI.",
    )
    parser.add_argument(
        "--skip-system-deps",
        action="store_true",
        help="Do not install OS packages. Useful for CI or managed hosts.",
    )
    parser.add_argument(
        "--package-manager",
        choices=("auto", "apt-get", "dnf", "pacman", "brew", "zypper"),
        default="auto",
        help="Package manager used for optional system dependencies.",
    )
    parser.add_argument(
        "--no-upgrade-pip",
        action="store_true",
        help="Skip pip/setuptools/wheel upgrade inside the venv.",
    )
    parser.add_argument(
        "--no-launcher",
        action="store_true",
        help="Do not write the workspace launcher scripts.",
    )
    parser.add_argument(
        "--no-desktop",
        action="store_true",
        help="Do not install the Linux desktop entry and icons.",
    )
    parser.add_argument(
        "--no-skills",
        action="store_true",
        help="Do not run rules_sync for Claude skill mirrors.",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip post-install import checks.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without changing files or installing packages.",
    )
    args = parser.parse_args(argv)
    args.venv = args.venv.expanduser()
    if not args.venv.is_absolute():
        args.venv = WORKSPACE_ROOT / args.venv
    return args


def _install_gui_system_dependencies(args: argparse.Namespace) -> None:
    manager = _detect_package_manager(args.package_manager)
    if manager is None:
        print(
            "No supported package manager found for GTK/VTE dependencies. "
            "Re-run with --skip-system-deps or install GTK/VTE manually.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    commands = _system_dependency_commands(manager)
    for command in commands:
        _run(command, args, cwd=WORKSPACE_ROOT)


def _detect_package_manager(requested: str) -> str | None:
    if requested != "auto":
        return requested
    for name in ("apt-get", "dnf", "pacman", "brew", "zypper"):
        if shutil.which(name):
            return name
    return None


def _system_dependency_commands(manager: str) -> list[list[str]]:
    sudo = [] if _running_as_root() or manager == "brew" else ["sudo"]
    if manager == "apt-get":
        return [
            [*sudo, "apt-get", "update"],
            [*sudo, "apt-get", "install", "-y", *APT_GUI_PACKAGES],
        ]
    if manager == "dnf":
        return [[*sudo, "dnf", "install", "-y", *DNF_GUI_PACKAGES]]
    if manager == "pacman":
        return [[*sudo, "pacman", "-Sy", "--noconfirm", "--needed", *PACMAN_GUI_PACKAGES]]
    if manager == "brew":
        return [["brew", "install", *BREW_GUI_PACKAGES]]
    if manager == "zypper":
        return [[*sudo, "zypper", "--non-interactive", "install", *_zypper_gui_packages()]]
    raise ValueError(f"unsupported package manager: {manager}")


def _zypper_gui_packages() -> tuple[str, ...]:
    version_prefix = f"python{sys.version_info.major}{sys.version_info.minor}"
    if version_prefix == "python36":
        python_packages = ("python3-gobject", "python3-gobject-Gdk", "python3-pycairo")
    else:
        python_packages = (
            f"{version_prefix}-gobject",
            f"{version_prefix}-gobject-Gdk",
            f"{version_prefix}-pycairo",
        )
    return (*python_packages, *ZYPPER_GUI_PACKAGES)


def _running_as_root() -> bool:
    geteuid = getattr(os, "geteuid", None)
    return bool(callable(geteuid) and geteuid() == 0)


def _ensure_venv(args: argparse.Namespace) -> Path:
    python = _venv_python(args.venv)
    if args.dry_run:
        print(f"Would create/update venv: {args.venv}")
        return python
    builder = venv.EnvBuilder(with_pip=True, system_site_packages=args.gui)
    builder.create(args.venv)
    return python


def _venv_python(venv_path: Path) -> Path:
    if platform.system() == "Windows":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def _install_python_dependencies(python: Path, args: argparse.Namespace) -> None:
    if not args.no_upgrade_pip:
        _run([str(python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], args)
    requirements = [REQUIREMENTS_ROOT / "runtime.txt"]
    if args.dev:
        requirements.append(REQUIREMENTS_ROOT / "dev.txt")
    for requirement in requirements:
        _run([str(python), "-m", "pip", "install", "-r", str(requirement)], args)


def _write_launcher(python: Path, args: argparse.Namespace) -> None:
    launchers = {
        WORKSPACE_ROOT / "agent-workspace.sh": _launcher_content(python, ()),
        WORKSPACE_ROOT / "agent-workspace-web.sh": _launcher_content(python, ("--ui", "web")),
        WORKSPACE_ROOT / "agent-workspace.command": _launcher_content(python, ("--ui", "web")),
        WORKSPACE_ROOT / "agent-workspace-web.command": _launcher_content(python, ("--ui", "web")),
        WORKSPACE_ROOT / "agent-workspace.cmd": _windows_launcher_content(python, ("--ui", "web")),
        WORKSPACE_ROOT / "agent-workspace-web.cmd": _windows_launcher_content(python, ("--ui", "web")),
    }
    if args.dry_run:
        for target in launchers:
            print(f"Would write launcher: {target}")
        return
    for target, content in launchers.items():
        target.write_text(content, encoding="utf-8")
        if target.suffix != ".cmd":
            target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _launcher_content(python: Path, default_args: tuple[str, ...]) -> str:
    args = " ".join(_shell_quote(arg) for arg in default_args)
    module_command = f'exec "{python}" -m agent_tools.agent_workspace'
    if args:
        module_command = f"{module_command} {args}"
    return "\n".join(
        [
            "#!/usr/bin/env sh",
            'WORKSPACE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)',
            'export PYTHONPATH="$WORKSPACE_ROOT${PYTHONPATH:+:$PYTHONPATH}"',
            f'{module_command} "$@"',
            "",
        ]
    )


def _windows_launcher_content(python: Path, default_args: tuple[str, ...]) -> str:
    args = " ".join(_windows_quote(arg) for arg in default_args)
    module_command = f'"{python}" -m agent_tools.agent_workspace'
    if args:
        module_command = f"{module_command} {args}"
    return "\r\n".join(
        [
            "@echo off",
            "setlocal",
            'set "WORKSPACE_ROOT=%~dp0"',
            'cd /d "%WORKSPACE_ROOT%"',
            'if defined PYTHONPATH (set "PYTHONPATH=%WORKSPACE_ROOT%;%PYTHONPATH%") else (set "PYTHONPATH=%WORKSPACE_ROOT%")',
            f"{module_command} %*",
            "exit /b %ERRORLEVEL%",
            "",
        ]
    )


def _shell_quote(value: str) -> str:
    if value and all(ch.isalnum() or ch in "-_./:" for ch in value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _windows_quote(value: str) -> str:
    if value and all(ch.isalnum() or ch in "-_./:" for ch in value):
        return value
    return '"' + value.replace('"', '""') + '"'


def _install_desktop_entry(python: Path, args: argparse.Namespace) -> None:
    if args.dry_run:
        print("Would install Agent Workspace desktop entry and icons.")
        return
    _run(
        [
            str(python),
            "-m",
            "agent_tools.agent_workspace.components.desktop_integration.src.install_desktop",
        ],
        args,
        env=_python_env(),
        cwd=WORKSPACE_ROOT,
    )


def _sync_agent_skills(python: Path, args: argparse.Namespace) -> None:
    _run(
        [str(python), "-m", "agent_tools.tools.rules_sync", "sync"],
        args,
        env=_python_env(),
        cwd=WORKSPACE_ROOT,
    )


def _validate_installation(python: Path, args: argparse.Namespace) -> None:
    _run(
        [
            str(python),
            "-c",
            "import yaml, tiktoken; import agent_tools.tools.task_context as tc; import agent_tools.agent_workspace.components.workspace_service.api; import agent_tools.agent_workspace.components.web_frontend.api; tc.token_count('Agent Workspace')",
        ],
        args,
        env=_python_env(),
        cwd=WORKSPACE_ROOT,
    )
    if args.gui:
        _run(
            [
                str(python),
                "-c",
                "import gi; gi.require_version('Gtk', '3.0')",
            ],
            args,
            env=_python_env(),
            cwd=WORKSPACE_ROOT,
        )


def _python_env() -> dict[str, str]:
    env = os.environ.copy()
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(WORKSPACE_ROOT) if not current else f"{WORKSPACE_ROOT}{os.pathsep}{current}"
    return env


def _run(
    command: list[str],
    args: argparse.Namespace,
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> None:
    printable = " ".join(command)
    if args.dry_run:
        print(f"Would run: {printable}")
        return
    print(f"Running: {printable}")
    subprocess.run(command, cwd=cwd, env=env, check=True)


if __name__ == "__main__":
    raise SystemExit(main())

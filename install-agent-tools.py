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
APT_WORKSPACE_PACKAGES = (
    "git",
    "graphviz",
    "plantuml",
    "python3",
    "python3-pip",
    "python3-venv",
)
DNF_WORKSPACE_PACKAGES = (
    "git",
    "graphviz",
    "plantuml",
    "python3",
    "python3-pip",
)
PACMAN_WORKSPACE_PACKAGES = (
    "git",
    "graphviz",
    "jdk-openjdk",
    "plantuml",
    "python",
    "python-pip",
)
BREW_WORKSPACE_PACKAGES = (
    "git",
    "graphviz",
    "plantuml",
    "python",
)
ZYPPER_WORKSPACE_PACKAGES = (
    "git",
    "graphviz",
    "plantuml",
    "python3",
    "python3-pip",
    "python3-venv",
)
APT_DOCKER_PACKAGES = ("docker.io",)
DNF_DOCKER_PACKAGES = ("docker",)
PACMAN_DOCKER_PACKAGES = ("docker",)
BREW_DOCKER_PACKAGES = ("docker",)
ZYPPER_DOCKER_PACKAGES = ("docker",)
INTERACTIVE_UI_CHOICES = ("web", "tk", "gtk")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not AGENT_TOOLS_ROOT.is_dir():
        print(f"agent_tools directory not found: {AGENT_TOOLS_ROOT}", file=sys.stderr)
        return 1

    if not args.skip_system_deps:
        _install_selected_system_dependencies(args)

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
    raw_argv = list(sys.argv[1:] if argv is None else argv)
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
        "--ui",
        choices=INTERACTIVE_UI_CHOICES,
        default=None,
        help="Preferred UI profile for dependency selection. GTK selects GTK/VTE system packages.",
    )
    parser.add_argument(
        "--system-tools",
        action="store_true",
        help="Install common workspace CLI packages such as git, PlantUML, and Graphviz.",
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Install Docker packages through the host package manager.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run the console setup wizard.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not run the setup wizard, even when launched from a terminal without flags.",
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
        "--recreate-venv-if-broken",
        action="store_true",
        help="Remove and recreate the target venv when its Python executable cannot start.",
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
    if args.ui == "gtk":
        args.gui = True
    if _should_run_interactive_setup(args, raw_argv):
        _run_interactive_setup(args)
    return args


def _should_run_interactive_setup(args: argparse.Namespace, raw_argv: list[str]) -> bool:
    if args.non_interactive:
        return False
    if args.interactive:
        return True
    return not raw_argv and sys.stdin.isatty() and not os.environ.get("CI")


def _run_interactive_setup(args: argparse.Namespace) -> None:
    print("Agent Workspace setup")
    print("=====================")
    print("This wizard keeps the old CLI flags available for CI, but guides normal local installs.")
    ui = _prompt_choice(
        "Which UI do you plan to use?",
        INTERACTIVE_UI_CHOICES,
        default=args.ui or ("gtk" if args.gui else "web"),
    )
    args.ui = ui
    args.gui = ui == "gtk"
    args.system_tools = _prompt_yes_no(
        "Install common system tools (git, PlantUML, Graphviz, Python venv/pip)?",
        default=True,
    )
    args.docker = _prompt_yes_no("Install Docker packages?", default=False)
    args.dev = _prompt_yes_no("Install developer/test Python dependencies?", default=args.dev)
    args.recreate_venv_if_broken = _prompt_yes_no(
        "Repair the Agent Workspace virtual environment if it is broken?",
        default=True,
    )
    if platform.system() == "Linux":
        args.no_desktop = not _prompt_yes_no("Install desktop launcher entry?", default=not args.no_desktop)
    install_system = args.gui or args.system_tools or args.docker
    if install_system:
        args.skip_system_deps = not _prompt_yes_no(
            "Allow installer to use the OS package manager for selected system dependencies?",
            default=not args.skip_system_deps,
        )
    print()
    print("Selected setup:")
    print(f"  UI profile: {args.ui}")
    print(f"  Python venv: {args.venv}")
    print(f"  Python developer deps: {_yes_no(args.dev)}")
    print(f"  Common system tools: {_yes_no(args.system_tools and not args.skip_system_deps)}")
    print(f"  Docker packages: {_yes_no(args.docker and not args.skip_system_deps)}")
    print(f"  GTK/VTE packages: {_yes_no(args.gui and not args.skip_system_deps)}")
    if not _prompt_yes_no("Continue?", default=True):
        raise SystemExit(0)


def _prompt_choice(prompt: str, choices: tuple[str, ...], *, default: str) -> str:
    default = default if default in choices else choices[0]
    suffix = "/".join(choice.upper() if choice == default else choice for choice in choices)
    while True:
        try:
            answer = input(f"{prompt} [{suffix}]: ").strip().lower()
        except EOFError:
            print()
            return default
        if not answer:
            return default
        if answer in choices:
            return answer
        print(f"Choose one of: {', '.join(choices)}")


def _prompt_yes_no(prompt: str, *, default: bool) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        try:
            answer = input(f"{prompt} [{suffix}]: ").strip().lower()
        except EOFError:
            print()
            return default
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Answer yes or no.")


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _install_selected_system_dependencies(args: argparse.Namespace) -> None:
    if not args.gui and not args.system_tools and not args.docker:
        return
    manager = _detect_package_manager(args.package_manager)
    if manager is None:
        print(
            "No supported package manager found for selected system dependencies. "
            "Re-run with --skip-system-deps or install GTK/VTE manually.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    packages = _selected_system_packages(manager, args)
    if not packages:
        return
    print(f"Installing system dependencies with {manager}: {', '.join(packages)}")
    commands = _system_dependency_commands(manager, packages)
    for command in commands:
        _run(command, args, cwd=WORKSPACE_ROOT)


def _detect_package_manager(requested: str) -> str | None:
    if requested != "auto":
        return requested
    for name in ("apt-get", "dnf", "pacman", "brew", "zypper"):
        if shutil.which(name):
            return name
    return None


def _selected_system_packages(manager: str, args: argparse.Namespace) -> tuple[str, ...]:
    packages: list[str] = []
    if args.system_tools:
        packages.extend(_workspace_system_packages(manager))
    if args.docker:
        packages.extend(_docker_system_packages(manager))
    if args.gui:
        packages.extend(_gui_system_packages(manager))
    return tuple(dict.fromkeys(packages))


def _workspace_system_packages(manager: str) -> tuple[str, ...]:
    if manager == "apt-get":
        return APT_WORKSPACE_PACKAGES
    if manager == "dnf":
        return DNF_WORKSPACE_PACKAGES
    if manager == "pacman":
        return PACMAN_WORKSPACE_PACKAGES
    if manager == "brew":
        return BREW_WORKSPACE_PACKAGES
    if manager == "zypper":
        return ZYPPER_WORKSPACE_PACKAGES
    raise ValueError(f"unsupported package manager: {manager}")


def _docker_system_packages(manager: str) -> tuple[str, ...]:
    if manager == "apt-get":
        return APT_DOCKER_PACKAGES
    if manager == "dnf":
        return DNF_DOCKER_PACKAGES
    if manager == "pacman":
        return PACMAN_DOCKER_PACKAGES
    if manager == "brew":
        return BREW_DOCKER_PACKAGES
    if manager == "zypper":
        return ZYPPER_DOCKER_PACKAGES
    raise ValueError(f"unsupported package manager: {manager}")


def _gui_system_packages(manager: str) -> tuple[str, ...]:
    if manager == "apt-get":
        return APT_GUI_PACKAGES
    if manager == "dnf":
        return DNF_GUI_PACKAGES
    if manager == "pacman":
        return PACMAN_GUI_PACKAGES
    if manager == "brew":
        return BREW_GUI_PACKAGES
    if manager == "zypper":
        return _zypper_gui_packages()
    raise ValueError(f"unsupported package manager: {manager}")


def _system_dependency_commands(manager: str, packages: tuple[str, ...]) -> list[list[str]]:
    sudo = [] if _running_as_root() or manager == "brew" else ["sudo"]
    if manager == "apt-get":
        return [
            [*sudo, "apt-get", "update"],
            [*sudo, "apt-get", "install", "-y", *packages],
        ]
    if manager == "dnf":
        return [[*sudo, "dnf", "install", "-y", *packages]]
    if manager == "pacman":
        return [[*sudo, "pacman", "-Sy", "--noconfirm", "--needed", *packages]]
    if manager == "brew":
        return [["brew", "install", *packages]]
    if manager == "zypper":
        return [[*sudo, "zypper", "--non-interactive", "install", *packages]]
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
    _check_venv_is_writable(args.venv)
    if _running_target_venv_python(python):
        _check_venv_python_runs(python)
        return python
    if python.exists() and not _venv_python_runs(python):
        if not args.recreate_venv_if_broken:
            _fail_unusable_venv(args.venv, subprocess.CalledProcessError(1, [str(python), "--version"]))
        _remove_broken_venv(args.venv)
    system_site_packages = args.gui or _venv_has_system_site_packages(args.venv)
    builder = venv.EnvBuilder(with_pip=True, system_site_packages=system_site_packages)
    try:
        builder.create(args.venv)
    except PermissionError as error:
        _fail_unwritable_venv(args.venv, error)
    except OSError as error:
        _fail_unusable_venv(args.venv, error)
    _check_venv_python_runs(python)
    return python


def _running_target_venv_python(python: Path) -> bool:
    try:
        return python.exists() and Path(sys.executable).resolve() == python.resolve()
    except OSError:
        return False


def _venv_has_system_site_packages(venv_path: Path) -> bool:
    config_path = venv_path / "pyvenv.cfg"
    try:
        config = config_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return any(
        line.partition("=")[2].strip().lower() == "true"
        for line in config.splitlines()
        if line.partition("=")[0].strip().lower() == "include-system-site-packages"
    )


def _check_venv_is_writable(venv_path: Path) -> None:
    if not venv_path.exists() or os.access(venv_path, os.W_OK):
        return
    _fail_unwritable_venv(venv_path)


def _fail_unwritable_venv(venv_path: Path, error: PermissionError | None = None) -> None:
    details = f": {error}" if error is not None else ""
    print(
        f"Cannot update Agent Workspace virtual environment{details}\n"
        f"Path: {venv_path}\n"
        "The directory exists but is not writable by the current user.\n"
        "Fix ownership or choose another venv, for example:\n"
        f"  sudo chown -R \"$(id -u):$(id -g)\" {venv_path}\n"
        "  python3 install-agent-tools.py --venv ~/.local/share/agent-tools/venv",
        file=sys.stderr,
    )
    raise SystemExit(1)


def _venv_python(venv_path: Path) -> Path:
    if platform.system() == "Windows":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python3"


def _check_venv_python_runs(python: Path) -> None:
    if _venv_python_runs(python):
        return
    _fail_unusable_venv(python.parent.parent, subprocess.CalledProcessError(1, [str(python), "--version"]))


def _venv_python_runs(python: Path) -> bool:
    try:
        subprocess.run([str(python), "--version"], check=True, stdout=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def _remove_broken_venv(venv_path: Path) -> None:
    protected_paths = {WORKSPACE_ROOT.resolve(), AGENT_TOOLS_ROOT.resolve(), Path.home().resolve()}
    try:
        resolved = venv_path.resolve()
    except OSError as error:
        _fail_unusable_venv(venv_path, error)
    if resolved in protected_paths or resolved.parent == resolved:
        raise SystemExit(f"Refusing to remove unsafe venv path: {venv_path}")
    print(f"Removing broken Agent Workspace virtual environment: {venv_path}")
    try:
        shutil.rmtree(venv_path)
    except PermissionError as error:
        _fail_unwritable_venv(venv_path, error)
    except OSError as error:
        _fail_unusable_venv(venv_path, error)


def _fail_unusable_venv(venv_path: Path, error: OSError | subprocess.CalledProcessError) -> None:
    reason = "The virtual environment may be stale or partially recreated."
    if isinstance(error, OSError) and getattr(error, "errno", None) == 26:
        reason = "A Python process may still be running from this virtual environment."
    print(
        "Cannot update Agent Workspace virtual environment\n"
        f"Path: {venv_path}\n"
        f"Error: {error}\n"
        f"{reason} Stop Agent Workspace processes using this venv, or remove "
        "the venv and run the installer again.",
        file=sys.stderr,
    )
    raise SystemExit(1)


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
    module_command = f"exec {_launcher_python_command(python)} -m agent_tools.agent_workspace"
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
    module_command = f"{_windows_launcher_python_command(python)} -m agent_tools.agent_workspace"
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


def _launcher_python_command(python: Path) -> str:
    try:
        relative = python.resolve().relative_to(WORKSPACE_ROOT.resolve())
    except (OSError, ValueError):
        return f'"{python}"'
    return '"$WORKSPACE_ROOT/' + relative.as_posix() + '"'


def _windows_launcher_python_command(python: Path) -> str:
    try:
        relative = python.resolve().relative_to(DEFAULT_VENV.resolve())
    except (OSError, ValueError):
        return _windows_quote(str(python))
    if relative.parts and relative.parts[-1].lower() in {"python", "python3", "python.exe"}:
        return '"%WORKSPACE_ROOT%agent_tools\\.venv\\Scripts\\python.exe"'
    return _windows_quote(str(python))


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
            "import clang.cindex, jsonschema, regex, tree_sitter, tree_sitter_cpp, yaml, tiktoken; import agent_tools.tools.task_context as tc; import agent_tools.agent_workspace.components.workspace_mcp.api; import agent_tools.agent_workspace.components.workspace_service.api; import agent_tools.agent_workspace.components.web_frontend.api; tc.token_count('Agent Workspace')",
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

"""Capability-driven dependency contracts for reusable environment images."""

from __future__ import annotations

class CapabilityRequirement:
    __slots__ = ("apt_packages", "pip_packages", "python_imports", "commands")

    def __init__(
        self,
        *,
        apt_packages: tuple[str, ...] = (),
        pip_packages: tuple[str, ...] = (),
        python_imports: tuple[str, ...] = (),
        commands: tuple[str, ...] = (),
    ) -> None:
        self.apt_packages = apt_packages
        self.pip_packages = pip_packages
        self.python_imports = python_imports
        self.commands = commands


CAPABILITY_REQUIREMENTS: dict[str, CapabilityRequirement] = {
    "workspace_tools": CapabilityRequirement(
        apt_packages=(
            "bash",
            "ca-certificates",
            "git",
            "python3",
            "python3-pip",
            "python3-venv",
        ),
        pip_packages=(
            "tree-sitter",
            "tree-sitter-cpp",
        ),
        python_imports=(
            "agent_tools",
            "tree_sitter",
            "tree_sitter_cpp",
        ),
        commands=(
            "python3 -m agent_tools.tools.cpp_light_code_map help",
        ),
    ),
    "cpp_source_analysis": CapabilityRequirement(
        apt_packages=(
            "clang",
            "libclang-dev",
            "python3-clang",
        ),
        python_imports=(
            "clang.cindex",
        ),
        commands=(
            "python3 -m agent_tools.tools.cpp_code_map help",
        ),
    ),
    "zephyr_pr_checks": CapabilityRequirement(
        apt_packages=(
            "clang-tidy",
            "coccinelle",
            "cppcheck",
            "libpq-dev",
            "lcov",
            "nodejs",
            "npm",
            "python3-dev",
            "python3-setuptools",
        ),
        pip_packages=(
            "codechecker",
        ),
        commands=(
            "CodeChecker version",
            "cppcheck --version",
            "node --version",
            "npm --version",
            "spatch --version",
            "genhtml --version",
        ),
    ),
    "agent_workspace_tests": CapabilityRequirement(
        apt_packages=(
            "gir1.2-gtk-3.0",
            "gir1.2-vte-2.91",
            "python3-gi",
            "python3-pytest",
            "python3-tk",
            "xvfb",
        ),
        python_imports=(
            "gi",
            "tkinter",
        ),
        commands=(
            "python3 -m pytest --version",
            "xvfb-run --help",
        ),
    ),
}


def normalize_capabilities(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    raise TypeError(f"image capabilities must be a string or list, got {type(value).__name__}")


def requirements_for_capabilities(capabilities: tuple[str, ...]) -> CapabilityRequirement:
    apt_packages: set[str] = set()
    pip_packages: set[str] = set()
    python_imports: set[str] = set()
    commands: set[str] = set()
    for capability in capabilities:
        try:
            requirement = CAPABILITY_REQUIREMENTS[capability]
        except KeyError as exc:
            raise ValueError(f"unknown environment image capability: {capability}") from exc
        apt_packages.update(requirement.apt_packages)
        pip_packages.update(requirement.pip_packages)
        python_imports.update(requirement.python_imports)
        commands.update(requirement.commands)
    return CapabilityRequirement(
        apt_packages=tuple(sorted(apt_packages)),
        pip_packages=tuple(sorted(pip_packages)),
        python_imports=tuple(sorted(python_imports)),
        commands=tuple(sorted(commands)),
    )


def baseline_check_command(capabilities: tuple[str, ...]) -> str:
    requirement = requirements_for_capabilities(capabilities)
    imports = "\n".join(f"import {module}" for module in requirement.python_imports)
    import_messages = "\n".join(f"print({module!r} + ' ok')" for module in requirement.python_imports)
    command_lines = [
        "set -euo pipefail",
        "python3 --version",
        "test -d agent_tools",
        "python3 - <<'PY'",
        imports,
        "",
        import_messages,
        "PY",
    ]
    for command in requirement.commands:
        command_lines.append(f"{command} >/tmp/{_command_stamp(command)}.help")
    return "\n".join(command_lines)


def _command_stamp(command: str) -> str:
    return command.replace("python3 -m ", "").replace(".", "_").replace(" ", "_").replace("-", "_")

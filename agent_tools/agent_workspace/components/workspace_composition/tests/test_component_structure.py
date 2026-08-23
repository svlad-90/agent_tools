from __future__ import annotations

import importlib
import ast
import re
import subprocess
import sys
from pathlib import Path

from agent_tools.tools.task_context import ensure_database as ensure_task_context_database


COMPONENTS = (
    "agent_status",
    "agent_runtime",
    "artifacts",
    "commands",
    "console_output",
    "desktop_integration",
    "gtk_desktop",
    "localization",
    "markdown",
    "process_runtime",
    "settings",
    "task_actions",
    "task_catalog",
    "task_context",
    "task_sessions",
    "test_support",
    "tk_frontend",
    "vte_terminal",
    "web_frontend",
    "workspace_composition",
    "workspace_service",
)

CLEAN_COMPONENTS = (
    "agent_status",
    "agent_runtime",
    "artifacts",
    "commands",
    "console_output",
    "desktop_integration",
    "gtk_desktop",
    "localization",
    "markdown",
    "process_runtime",
    "settings",
    "task_actions",
    "task_catalog",
    "task_context",
    "task_sessions",
    "test_support",
    "tk_frontend",
    "vte_terminal",
    "web_frontend",
    "workspace_composition",
    "workspace_service",
)

PORTABLE_COMPONENTS = tuple(
    component
    for component in COMPONENTS
    if component not in {"gtk_desktop", "test_support", "tk_frontend", "vte_terminal"}
)

REMOVED_ROOT_FACADES = (
    "artifacts.py",
    "commands.py",
    "gtk_i18n.py",
    "gtk_language_instructions.json",
    "gtk_translations.json",
    "gtk_ui_strings.json",
    "task_action_files.py",
    "task_action_menu.py",
    "task_action_model.py",
    "task_action_state.py",
    "tk_strings.py",
    "tk_strings.json",
    "workspace_strings.py",
    "workspace_strings.json",
    "gtk_open.py",
    "gtk_task_helpers.py",
    "gtk_task_style.py",
    "gtk_terminal.py",
    "gtk_terminal_ui.py",
    "gtk_theme.py",
    "gtk_ui.py",
    "gtk_widgets.py",
    "ui.py",
    "vte_terminal.py",
    "web_ui.py",
    "service.py",
    "core.py",
    "install_desktop.py",
)


def test_agent_workspace_components_have_api_docs_src_layout() -> None:
    root = _components_root()

    for component in COMPONENTS:
        component_dir = root / component
        assert (component_dir / "__init__.py").is_file()
        assert (component_dir / "api" / "__init__.py").is_file()
        assert (component_dir / "docs" / "README.md").is_file()
        assert (component_dir / "src" / "__init__.py").is_file()


def test_agent_workspace_component_api_modules_import_without_gtk() -> None:
    code = "\n".join(
        [
            "import importlib",
            "import sys",
            f"components = {PORTABLE_COMPONENTS!r}",
            "for component in components:",
            "    importlib.import_module(f'agent_tools.agent_workspace.components.{component}.api')",
            "assert 'gi' not in sys.modules",
        ]
    )

    subprocess.run([sys.executable, "-c", code], check=True)


def test_task_catalog_api_import_does_not_import_agent_workspace_core() -> None:
    code = "\n".join(
        [
            "import importlib",
            "import sys",
            "importlib.import_module('agent_tools.agent_workspace.components.task_catalog.api')",
            "assert 'agent_tools.agent_workspace.core' not in sys.modules",
        ]
    )

    subprocess.run([sys.executable, "-c", code], check=True)


def test_task_catalog_component_discovers_tasks(tmp_path: Path) -> None:
    from agent_tools.agent_workspace.components.task_catalog.api import discover_tasks

    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    ensure_task_context_database(task)

    tasks = discover_tasks(tmp_path)

    assert [entry.name for entry in tasks] == ["sample-task"]
    assert tasks[0].has_context


def test_agent_workspace_component_api_exports_are_explicit() -> None:
    for component in COMPONENTS:
        exported = _api_all_exports(component)
        assert exported
        assert all(isinstance(name, str) and name for name in exported)


def test_agent_workspace_component_api_exports_no_private_names() -> None:
    offenders: dict[str, list[str]] = {}
    for component in COMPONENTS:
        private_exports = [name for name in _api_all_exports(component) if name.startswith("_")]
        if private_exports:
            offenders[component] = private_exports

    assert offenders == {}


def test_extracted_components_do_not_use_legacy_adapters() -> None:
    root = _components_root()

    for component in CLEAN_COMPONENTS:
        assert not (root / component / "src" / "legacy.py").exists()
        api_source = (root / component / "api" / "__init__.py").read_text(encoding="utf-8")
        assert ".legacy" not in api_source


def test_agent_workspace_root_has_no_component_facades() -> None:
    root = _agent_workspace_root()

    assert [name for name in REMOVED_ROOT_FACADES if (root / name).exists()] == []


def test_agent_workspace_service_uses_component_apis() -> None:
    service_path = _components_root() / "workspace_service" / "src" / "service.py"
    service_source = service_path.read_text(encoding="utf-8")

    assert "from ..." in service_source
    assert "from ....core import" not in service_source
    assert "from ....artifacts import" not in service_source
    assert "from ....commands import" not in service_source


def test_agent_workspace_component_src_is_not_imported_outside_components() -> None:
    root = _agent_workspace_root()
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if path.name == "test_component_structure.py":
            continue
        relative_parts = path.relative_to(root).parts
        if relative_parts[:1] == ("components",):
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"^\s*(?:from|import)\s+.*\.components\.[^\n]+\.src\b", text, re.MULTILINE):
            offenders.append(str(path.relative_to(root)))

    assert offenders == []


def test_agent_workspace_tests_live_under_components() -> None:
    root = _agent_workspace_root()
    tests_root = root / "tests"
    central_component_tests = _components_root() / "tests"

    root_tests = list(tests_root.glob("test_*.py")) if tests_root.exists() else []
    central_tests = list(central_component_tests.glob("test_*.py")) if central_component_tests.exists() else []

    assert root_tests == []
    assert central_tests == []


def test_localization_component_uses_neutral_catalog_names() -> None:
    root = _components_root() / "localization" / "src"
    legacy_names = {
        "gtk_i18n.py",
        "gtk_language_instructions.json",
        "gtk_translations.json",
        "gtk_ui_strings.json",
        "tk_strings.py",
        "tk_strings.json",
        "workspace_strings.py",
        "workspace_strings.json",
    }

    assert sorted(path.name for path in root.iterdir() if path.name in legacy_names) == []


def test_agent_workspace_production_components_do_not_import_other_component_src() -> None:
    root = _components_root()
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if "tests" in path.relative_to(root).parts:
            continue
        relative_parts = path.relative_to(root).parts
        if len(relative_parts) < 3:
            continue
        component = relative_parts[0]
        if component == "test_support":
            continue
        if relative_parts[1] == "api":
            continue
        text = path.read_text(encoding="utf-8")
        pattern = re.compile(
            r"^\s*(?:from|import)\s+agent_tools\.tools\.agent_workspace\.components\.([^.]+)\.src\b",
            re.MULTILINE,
        )
        for match in pattern.finditer(text):
            if match.group(1) != component:
                offenders.append(str(path.relative_to(root)))
                break
        relative_pattern = re.compile(r"^\s*from\s+(\.+)([^.\s]+)\.src\b", re.MULTILINE)
        for match in relative_pattern.finditer(text):
            dots = match.group(1)
            target = match.group(2)
            if len(dots) >= 3 and target != component:
                offenders.append(str(path.relative_to(root)))
                break

    assert sorted(set(offenders)) == []


def test_agent_workspace_runtime_code_does_not_import_test_support() -> None:
    root = _agent_workspace_root()
    offenders: list[str] = []
    pattern = re.compile(r"agent_tools\.tools\.agent_workspace\.components\.test_support")
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        relative_parts = path.relative_to(root).parts
        if "tests" in relative_parts:
            continue
        if relative_parts[:2] == ("components", "test_support"):
            continue
        if pattern.search(path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(root)))

    assert offenders == []


def _agent_workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _components_root() -> Path:
    return _agent_workspace_root() / "components"


def _api_all_exports(component: str) -> tuple[str, ...]:
    api_path = _components_root() / component / "api" / "__init__.py"
    module = ast.parse(api_path.read_text(encoding="utf-8"), filename=str(api_path))
    for node in module.body:
        if isinstance(node, ast.Assign):
            if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
                continue
            value = ast.literal_eval(node.value)
            assert isinstance(value, list)
            return tuple(value)
    return ()

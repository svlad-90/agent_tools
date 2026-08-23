from __future__ import annotations

from agent_tools.tools.agent_workspace.components.test_support.src.helpers import *


def test_agent_workspace_desktop_uses_icon_name() -> None:
    desktop = Path(__file__).resolve().parents[4] / "agent-workspace.desktop"
    content = desktop.read_text(encoding="utf-8")

    assert "Icon=agent-workspace\n" in content
    assert "StartupWMClass=agent-workspace\n" in content


def test_agent_workspace_web_launcher_uses_web_backend() -> None:
    workspace = Path(__file__).resolve().parents[4]
    launchers = [
        workspace / "agent-workspace-web.sh",
        workspace / "agent-workspace-web.command",
        workspace / "agent-workspace-web.cmd",
    ]

    for launcher in launchers:
        content = launcher.read_text(encoding="utf-8")
        assert "agent_tools.tools.agent_workspace" in content
        assert "--ui web" in content

    assert '"$@"' in launchers[0].read_text(encoding="utf-8")
    assert '"$@"' in launchers[1].read_text(encoding="utf-8")
    assert "%*" in launchers[2].read_text(encoding="utf-8")


def test_agent_workspace_portable_default_launchers_use_web_backend() -> None:
    workspace = Path(__file__).resolve().parents[4]
    launchers = [
        workspace / "agent-workspace.command",
        workspace / "agent-workspace.cmd",
    ]

    for launcher in launchers:
        content = launcher.read_text(encoding="utf-8")
        assert "agent_tools.tools.agent_workspace" in content
        assert "--ui web" in content


def test_agent_workspace_desktop_entry_uses_current_workspace_path(tmp_path: Path) -> None:
    content = desktop_entry(tmp_path)

    assert f"Exec={tmp_path / 'agent-workspace.sh'}\n" in content
    assert f"Path={tmp_path}\n" in content
    assert "/Projects/new_dev" not in content


def test_install_agent_tools_writes_auto_and_web_launchers(tmp_path: Path) -> None:
    installer_path = Path(__file__).resolve().parents[4] / "install-agent-tools.py"
    spec = importlib.util.spec_from_file_location("install_agent_tools_test", installer_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    python = tmp_path / ".venv" / "bin" / "python"
    auto = module._launcher_content(python, ())
    web = module._launcher_content(python, ("--ui", "web"))
    mac_auto = module._launcher_content(python, ("--ui", "web"))
    windows_auto = module._windows_launcher_content(Path("C:/agent_tools/.venv/Scripts/python.exe"), ("--ui", "web"))
    windows_web = module._windows_launcher_content(Path("C:/agent_tools/.venv/Scripts/python.exe"), ("--ui", "web"))

    assert "agent_tools.tools.agent_workspace" in auto
    assert "--ui web" not in auto
    assert "agent_tools.tools.agent_workspace --ui web" in web
    assert "agent_tools.tools.agent_workspace --ui web" in mac_auto
    assert "agent_tools.tools.agent_workspace --ui web" in windows_auto
    assert '"$@"' in web
    assert "agent_tools.tools.agent_workspace --ui web" in windows_web
    assert "%*" in windows_web


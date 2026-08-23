from __future__ import annotations

from agent_tools.agent_workspace.components.test_support.src.helpers import *


def test_agent_workspace_auto_ui_falls_back_to_web_before_tk(monkeypatch: object) -> None:
    calls: list[str] = []

    def fake_load_ui_main(name: str):
        calls.append(name)
        if name == "gtk":
            raise ImportError("GTK missing")

        def fake_main(argv: list[str] | None = None) -> int:
            assert argv == ["--workspace", "/tmp/ws"]
            return 7

        return fake_main

    monkeypatch.setattr(agent_workspace_main_module, "_load_ui_main", fake_load_ui_main)

    assert agent_workspace_main_module.main(["--workspace", "/tmp/ws"]) == 7
    assert calls == ["gtk", "web"]


def test_agent_workspace_auto_ui_uses_web_only_on_portable_platforms(monkeypatch: object) -> None:
    monkeypatch.setattr(agent_workspace_main_module.platform, "system", lambda: "Windows")

    assert agent_workspace_main_module._auto_ui_order() == ("web",)

    monkeypatch.setattr(agent_workspace_main_module.platform, "system", lambda: "Darwin")

    assert agent_workspace_main_module._auto_ui_order() == ("web",)


def test_agent_workspace_explicit_web_ui_uses_web_backend(monkeypatch: object) -> None:
    calls: list[str] = []

    def fake_load_ui_main(name: str):
        calls.append(name)

        def fake_main(argv: list[str] | None = None) -> int:
            assert argv == ["--workspace", "/tmp/ws"]
            return 0

        return fake_main

    monkeypatch.setattr(agent_workspace_main_module, "_load_ui_main", fake_load_ui_main)

    assert agent_workspace_main_module.main(["--ui", "web", "--workspace", "/tmp/ws"]) == 0
    assert calls == ["web"]


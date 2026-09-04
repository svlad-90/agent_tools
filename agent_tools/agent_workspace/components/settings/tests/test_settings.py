from __future__ import annotations

import io
import subprocess
import tarfile

from agent_tools.agent_workspace.components.test_support.src.helpers import *


def test_agent_workspace_settings_persist_font_size(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"

    save_agent_workspace_settings(
        {
            "text_font_size": 17,
            "button_font_size": 14,
            "theme": "dark",
            "language": "ru",
            "default_agent": "claude",
            "default_codex_model": "gpt-5.5",
            "default_codex_reasoning": "medium",
            "default_claude_model": "sonnet",
            "default_claude_effort": "low",
            "codex_animations_enabled": True,
            "claude_animations_enabled": True,
            "limited_bash_output_tokens": 12_000,
            "limited_bash_head_tokens": 2_000,
            "limited_bash_tail_tokens": 3_000,
            "limited_bash_heartbeat_seconds": 15,
            "limited_bash_heartbeat_tokens": 700,
            "system_prompt": "Prefer short, concrete answers.\nKeep task state durable.",
            "inject_task_context_prompt": False,
            "mcp_enabled_groups": ["search", "python", "task_context"],
            "mcp_trusted": True,
            "task_dictionary_auto_discovery": False,
            "task_dictionary_min_occurrences": 3,
            "task_dictionary_min_saving": 24,
            "task_dictionary_min_term_length": 10,
            "task_dictionary_max_term_words": 4,
            "task_dictionary_strip_articles": False,
            "task_dictionary_preview_text": "Agent Workspace Agent Workspace",
            "geometry": "1200x800+10+20",
            "main_split_ratio": 0.3,
            "details_split_ratio": 0.7,
            "actions_split_ratio": 0.4,
            "last_workspace": str(tmp_path / "workspace"),
            "recent_workspaces": [str(tmp_path / "workspace"), str(tmp_path / "other")],
        },
        settings_path,
    )

    assert load_agent_workspace_settings(settings_path) == {
        "text_font_size": 17,
        "button_font_size": 14,
        "theme": "dark",
        "language": "ru",
        "default_agent": "claude",
        "default_codex_model": "gpt-5.5",
        "default_codex_reasoning": "medium",
        "default_claude_model": "sonnet",
        "default_claude_effort": "low",
        "codex_animations_enabled": True,
        "claude_animations_enabled": True,
        "limited_bash_output_tokens": 12_000,
        "limited_bash_head_tokens": 2_000,
        "limited_bash_tail_tokens": 3_000,
        "limited_bash_heartbeat_seconds": 15,
        "limited_bash_heartbeat_tokens": 700,
        "system_prompt": "Prefer short, concrete answers.\nKeep task state durable.",
        "inject_task_context_prompt": False,
        "mcp_enabled_groups": (
            "search",
            "python",
            "task_context",
            "task_actions",
            "commit_messages",
            "validation",
        ),
        "mcp_trusted": True,
        "task_dictionary_auto_discovery": False,
        "task_dictionary_min_occurrences": 3,
        "task_dictionary_min_saving": 24,
        "task_dictionary_min_term_length": 10,
        "task_dictionary_max_term_words": 4,
        "task_dictionary_strip_articles": False,
        "task_dictionary_preview_text": "Agent Workspace Agent Workspace",
        "geometry": "1200x800+10+20",
        "main_split_ratio": 0.3,
        "details_split_ratio": 0.7,
        "actions_split_ratio": 0.4,
        "last_workspace": str(tmp_path / "workspace"),
        "recent_workspaces": [str(tmp_path / "workspace"), str(tmp_path / "other")],
    }


def test_remember_agent_workspace_updates_last_and_recent(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    old_workspace = tmp_path / "old"
    new_workspace = tmp_path / "new"
    save_agent_workspace_settings(
        {
            "theme": "dark",
            "last_workspace": str(old_workspace),
            "recent_workspaces": [str(old_workspace)],
        },
        settings_path,
    )

    settings = remember_agent_workspace(new_workspace, settings_path)

    assert settings["theme"] == "dark"
    assert settings["last_workspace"] == str(new_workspace.resolve())
    assert settings["recent_workspaces"] == [str(new_workspace.resolve()), str(old_workspace)]


def test_agent_workspace_settings_migrate_old_font_size(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text('{"font_size": 17}', encoding="utf-8")

    assert load_agent_workspace_settings(settings_path) == {"text_font_size": 17}


def test_agent_workspace_setting_or_default_treats_blank_as_missing() -> None:
    settings = {
        "default_codex_model": "",
        "default_codex_reasoning": " ",
        "default_claude_model": " sonnet ",
    }

    assert agent_workspace_setting_or_default(settings, "default_codex_model", "gpt-5.5") == "gpt-5.5"
    assert agent_workspace_setting_or_default(settings, "default_codex_reasoning", "medium") == "medium"
    assert agent_workspace_setting_or_default(settings, "default_claude_model", "opus") == "sonnet"
    assert agent_workspace_setting_or_default(settings, "default_claude_effort", "medium") == "medium"


def test_agent_workspace_runtime_settings_disables_agent_animations_by_default() -> None:
    settings = agent_workspace_runtime_settings({}, default_font_size=13)

    assert settings.codex_animations_enabled is False
    assert settings.claude_animations_enabled is False
    assert settings.limited_bash_output_tokens == AGENT_WORKSPACE_DEFAULT_LIMITED_BASH_OUTPUT_TOKENS
    assert settings.limited_bash_head_tokens == AGENT_WORKSPACE_DEFAULT_LIMITED_BASH_HEAD_TOKENS
    assert settings.limited_bash_tail_tokens == AGENT_WORKSPACE_DEFAULT_LIMITED_BASH_TAIL_TOKENS
    assert settings.limited_bash_heartbeat_seconds == AGENT_WORKSPACE_DEFAULT_LIMITED_BASH_HEARTBEAT_SECONDS
    assert settings.limited_bash_heartbeat_tokens == AGENT_WORKSPACE_DEFAULT_LIMITED_BASH_HEARTBEAT_TOKENS
    assert settings.mcp_enabled_groups == tuple(group_id for group_id, _label in workspace_mcp_tool_groups())
    assert workspace_mcp_enabled_groups_for_runtime(settings.mcp_enabled_groups) is None
    assert settings.mcp_trusted is False


def test_workspace_mcp_tool_groups_have_tooltips() -> None:
    for group_id, _label in workspace_mcp_tool_groups():
        assert workspace_mcp_tool_group_tooltip(group_id)


def test_workspace_mcp_required_groups_cannot_be_disabled() -> None:
    settings = agent_workspace_runtime_settings(
        {
            "mcp_enabled_groups": ["search"],
        },
        default_font_size=13,
    )

    enabled = set(settings.mcp_enabled_groups)

    assert "search" in enabled
    assert {group_id for group_id, _label in workspace_mcp_required_tool_groups()} <= enabled
    assert not ({group_id for group_id, _label in workspace_mcp_required_tool_groups()} & {group_id for group_id, _label in workspace_mcp_configurable_tool_groups()})


def test_apply_agent_workspace_mcp_trust_updates_codex_and_claude_settings(tmp_path: Path) -> None:
    codex_path = tmp_path / "codex" / "config.toml"
    claude_path = tmp_path / "claude" / "settings.json"
    codex_path.parent.mkdir()
    codex_path.write_text(
        'model = "gpt-5.5"\n\n[mcp_servers.agent_tools_workspace]\ncommand = "python"\n',
        encoding="utf-8",
    )
    claude_path.parent.mkdir()
    claude_path.write_text('{"theme": "dark", "permissions": {"allow": ["Bash(git status)"]}}\n', encoding="utf-8")

    apply_agent_workspace_mcp_trust(trusted=True, codex_path=codex_path, claude_path=claude_path)

    assert 'default_tools_approval_mode = "approve"' in codex_path.read_text(encoding="utf-8")
    claude_data = json.loads(claude_path.read_text(encoding="utf-8"))
    assert "mcp__agent-tools__*" in claude_data["permissions"]["allow"]

    apply_agent_workspace_mcp_trust(trusted=False, codex_path=codex_path, claude_path=claude_path)

    assert 'default_tools_approval_mode = "prompt"' in codex_path.read_text(encoding="utf-8")
    claude_data = json.loads(claude_path.read_text(encoding="utf-8"))
    assert claude_data["permissions"]["allow"] == ["Bash(git status)"]


def test_agent_workspace_runtime_settings_normalizes_ui_defaults() -> None:
    settings = agent_workspace_runtime_settings(
        {
            "text_font_size": 17,
            "button_font_size": 15,
            "theme": "dark",
            "language": "en",
            "default_agent": "claude",
            "default_codex_model": "",
            "default_codex_reasoning": " ",
            "default_claude_model": "",
            "default_claude_effort": "",
            "codex_animations_enabled": True,
            "claude_animations_enabled": True,
            "limited_bash_output_tokens": 4_000,
            "limited_bash_head_tokens": 2_500,
            "limited_bash_tail_tokens": 1_500,
            "limited_bash_heartbeat_seconds": 10,
            "limited_bash_heartbeat_tokens": 900,
            "system_prompt": "Use the project-specific policy.",
            "inject_task_context_prompt": False,
            "mcp_enabled_groups": ["search", "unknown", "validation"],
            "mcp_trusted": True,
            "task_dictionary_auto_discovery": False,
            "task_dictionary_min_occurrences": 4,
            "task_dictionary_min_saving": 32,
            "task_dictionary_min_term_length": 12,
            "task_dictionary_max_term_words": 5,
            "task_dictionary_strip_articles": False,
            "task_dictionary_preview_text": "Custom preview text",
            "geometry": "1280x900+1+2",
            "main_split_ratio": 0.3,
            "details_split_ratio": "0.7",
            "actions_split_ratio": 0.42,
        },
        default_font_size=13,
    )

    assert settings.text_font_size == 17
    assert settings.button_font_size == 15
    assert settings.theme == "dark"
    assert settings.language == "en"
    assert settings.default_agent == "claude"
    assert settings.default_codex_model == "gpt-5.5"
    assert settings.default_codex_reasoning == "medium"
    assert settings.default_claude_model == "sonnet"
    assert settings.default_claude_effort == "medium"
    assert settings.codex_animations_enabled is True
    assert settings.claude_animations_enabled is True
    assert settings.limited_bash_output_tokens == 4_000
    assert settings.limited_bash_head_tokens == 2_500
    assert settings.limited_bash_tail_tokens == 1_500
    assert settings.limited_bash_heartbeat_seconds == 10
    assert settings.limited_bash_heartbeat_tokens == 900
    assert settings.system_prompt == "Use the project-specific policy."
    assert settings.inject_task_context_prompt is False
    assert settings.mcp_enabled_groups == (
        "search",
        "task_context",
        "task_actions",
        "commit_messages",
        "validation",
    )
    assert settings.mcp_trusted is True
    assert settings.task_dictionary_auto_discovery is False
    assert settings.task_dictionary_min_occurrences == 4
    assert settings.task_dictionary_min_saving == 32
    assert settings.task_dictionary_min_term_length == 12
    assert settings.task_dictionary_max_term_words == 5
    assert settings.task_dictionary_strip_articles is False
    assert settings.task_dictionary_preview_text == "Custom preview text"
    assert settings.window_geometry == "1280x900+1+2"
    assert settings.main_split_ratio == 0.3
    assert settings.details_split_ratio == 0.7
    assert settings.actions_split_ratio == 0.42

    policy = task_dictionary_policy_from_runtime_settings(settings)
    assert policy.auto_discovery is False
    assert policy.min_occurrences == 4
    assert policy.min_saving == 32
    assert policy.min_term_length == 12
    assert policy.max_term_words == 5
    assert policy.strip_articles is False


def test_agent_workspace_runtime_settings_falls_back_for_invalid_values() -> None:
    settings = agent_workspace_runtime_settings(
        {
            "text_font_size": "17",
            "button_font_size": "15",
            "theme": "blue",
            "language": "bad",
            "default_agent": "bad",
            "task_dictionary_min_occurrences": 0,
            "task_dictionary_min_saving": -1,
            "task_dictionary_min_term_length": 0,
            "task_dictionary_max_term_words": 99,
            "limited_bash_output_tokens": 12,
            "limited_bash_head_tokens": 12,
            "limited_bash_tail_tokens": 300_000,
            "limited_bash_heartbeat_seconds": 0,
            "limited_bash_heartbeat_tokens": -1,
            "task_dictionary_preview_text": "",
            "geometry": 42,
            "main_split_ratio": 2.0,
            "details_split_ratio": "bad",
            "actions_split_ratio": 0.01,
        },
        default_font_size=13,
        default_language="uk",
    )

    assert settings.text_font_size == 13
    assert settings.button_font_size == 13
    assert settings.theme == "light"
    assert settings.language == "uk"
    assert settings.default_agent == "codex"
    assert settings.system_prompt == ""
    assert settings.inject_task_context_prompt is True
    assert settings.task_dictionary_auto_discovery is True
    assert settings.task_dictionary_min_occurrences == 1
    assert settings.task_dictionary_min_saving == 0
    assert settings.task_dictionary_min_term_length == 1
    assert settings.task_dictionary_max_term_words == 20
    assert settings.limited_bash_output_tokens == 100
    assert settings.limited_bash_head_tokens == 100
    assert settings.limited_bash_tail_tokens == 200_000
    assert settings.limited_bash_heartbeat_seconds == 1
    assert settings.limited_bash_heartbeat_tokens == 0
    assert settings.task_dictionary_strip_articles is True
    assert settings.task_dictionary_preview_text == DICTIONARY_PREVIEW_TEXT
    assert len(settings.task_dictionary_preview_text) > 5_000
    assert "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py" in settings.task_dictionary_preview_text
    assert "TASK_CONTEXT.sqlite3" in settings.task_dictionary_preview_text
    assert settings.window_geometry == "1180x760"
    assert settings.main_split_ratio == 0.25
    assert settings.details_split_ratio == 0.25
    assert settings.actions_split_ratio == 0.38


def test_agent_workspace_settings_migrates_legacy_bash_char_limit(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text('{"limited_bash_output_chars": 8000}', encoding="utf-8")

    loaded = load_agent_workspace_settings(settings_path)
    settings = agent_workspace_runtime_settings(loaded, default_font_size=13)

    assert loaded["limited_bash_output_tokens"] == 2_000
    assert loaded["limited_bash_head_tokens"] == 2_000
    assert loaded["limited_bash_tail_tokens"] == 2_000
    assert settings.limited_bash_output_tokens == 2_000
    assert settings.limited_bash_head_tokens == 2_000
    assert settings.limited_bash_tail_tokens == 2_000


def test_agent_workspace_runtime_settings_migrates_legacy_dictionary_preview_text() -> None:
    settings = agent_workspace_runtime_settings(
        {"task_dictionary_preview_text": LEGACY_DICTIONARY_PREVIEW_TEXT},
        default_font_size=13,
    )

    assert settings.task_dictionary_preview_text == DICTIONARY_PREVIEW_TEXT
    assert len(settings.task_dictionary_preview_text) > 5_000


def test_agent_workspace_runtime_settings_migrates_earliest_short_dictionary_preview_text() -> None:
    earliest_preview = (
        "Agent Workspace renders TASK_CONTEXT.sqlite3 entries. "
        "Agent Workspace Details can show encoded task context. "
        "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py validates Agent Workspace behavior."
    )

    settings = agent_workspace_runtime_settings(
        {"task_dictionary_preview_text": earliest_preview},
        default_font_size=13,
    )

    assert len(earliest_preview) < 1_000
    assert settings.task_dictionary_preview_text == DICTIONARY_PREVIEW_TEXT


def test_ai_agent_model_settings_selects_per_agent_defaults() -> None:
    codex_settings = ai_agent_model_settings(
        "codex",
        codex_model="gpt-5.5",
        codex_reasoning="medium",
        claude_model="sonnet",
        claude_effort="low",
    )
    claude_settings = ai_agent_model_settings(
        "claude",
        codex_model="gpt-5.5",
        codex_reasoning="medium",
        claude_model="sonnet",
        claude_effort="low",
    )

    assert codex_settings.model == "gpt-5.5"
    assert codex_settings.reasoning_effort == "medium"
    assert claude_settings.model == "sonnet"
    assert claude_settings.reasoning_effort == "low"


def test_ai_agent_model_settings_preserves_blank_values() -> None:
    settings = ai_agent_model_settings(
        "unknown",
        codex_model="",
        codex_reasoning="",
        claude_model="sonnet",
        claude_effort="medium",
    )

    assert settings.model == ""
    assert settings.reasoning_effort == ""


def test_agent_workspace_settings_clamp_bad_font_size(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        (
            '{"text_font_size": 100, "button_font_size": 4, '
            '"theme": "blue", "language": "bad", "default_agent": "bad", '
            '"default_codex_reasoning": "bad", "default_claude_effort": "bad", "geometry": "bad"}'
        ),
        encoding="utf-8",
    )

    assert load_agent_workspace_settings(settings_path) == {
        "text_font_size": 28,
        "button_font_size": 8,
    }


def test_agent_executable_checks_path_and_local_bin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("HOME", str(tmp_path))

    assert agent_executable("claude") is None

    local_claude = tmp_path / ".local" / "bin" / "claude"
    local_claude.parent.mkdir(parents=True)
    local_claude.write_text("#!/bin/sh\n", encoding="utf-8")

    assert agent_executable("claude") == str(local_claude)


def test_agent_install_commands_are_available() -> None:
    assert agent_install_command("codex") == "npm install -g @openai/codex"
    assert agent_install_command("claude") == "npm install -g @anthropic-ai/claude-code"


def test_codex_model_choices_loads_model_cache_slugs(tmp_path: Path) -> None:
    cache = tmp_path / "models_cache.json"
    cache.write_text(
        json.dumps(
            {
                "models": [
                    {"slug": "gpt-5.6-sol"},
                    {"slug": "gpt-5.5"},
                    {"slug": "gpt-5.5"},
                    {"display_name": "missing slug"},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert codex_model_choices(cache) == ("gpt-5.6-sol", "gpt-5.5")


def test_codex_model_choices_info_uses_real_cli_catalog(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = bin_dir / "codex"
    codex.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' 'WARNING: ignored setup warning'\n"
        "printf '%s\\n' '{\"models\":["
        "{\"slug\":\"gpt-5.6-sol\",\"model_messages\":{\"instructions_template\":\"large\"}},"
        "{\"slug\":\"gpt-5.5\"},"
        "{\"slug\":\"gpt-5.6-sol\"}"
        "]}'\n",
        encoding="utf-8",
    )
    codex.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir))

    info = codex_model_choices_info()

    assert info.choices == ("gpt-5.6-sol", "gpt-5.5")
    assert info.source == "Codex CLI: codex debug models"


def test_codex_model_choices_info_can_skip_live_cli_for_fast_settings_open(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cache = tmp_path / "models_cache.json"
    cache.write_text(json.dumps({"models": [{"slug": "cached-model"}]}), encoding="utf-8")
    monkeypatch.setenv("PATH", "")

    info = codex_model_choices_info(cache, use_cli=False)

    assert info.choices == ("cached-model",)
    assert info.source == f"Codex cache: {cache}"


def test_claude_model_choices_info_includes_configured_models(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(
        json.dumps({"model": "claude-opus-4-1", "nested": {"fallbackModel": "claude-sonnet-4"}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))

    info = claude_model_choices_info()

    assert "claude-opus-4-1" in info.choices
    assert "claude-sonnet-4" in info.choices
    assert "sonnet" in info.choices
    assert "fable" not in info.choices
    assert info.source == "Claude settings"


def test_claude_model_choices_info_falls_back_when_cli_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("HOME", "/missing-agent-workspace-home")

    info = claude_model_choices_info()

    assert info.choices == ("sonnet", "opus")
    assert info.source == "fallback"


def test_agent_workspace_root_resolves_from_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "agent_tools").mkdir(parents=True)
    (workspace / "install-agent-tools.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    assert agent_workspace_root(workspace / "agent_tools") == workspace


def test_agent_workspace_update_commands_install_only(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "agent_tools").mkdir(parents=True)
    (workspace / "install-agent-tools.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    commands = agent_workspace_update_commands(workspace, python_executable="/python")

    assert commands == ((
        "/python",
        str(workspace / "install-agent-tools.py"),
        "--non-interactive",
        "--skip-system-deps",
        "--recreate-venv-if-broken",
    ),)


def test_run_agent_workspace_update_returns_failed_installer_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "agent_tools").mkdir(parents=True)
    (workspace / "agent_tools" / "VERSION").write_text("2.0.0\n", encoding="utf-8")
    (workspace / "install-agent-tools.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    tarball = _agent_workspace_release_tarball()

    def fake_run(
        command: tuple[str, ...],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 7, stdout="stdout text\n", stderr="stderr text\n")

    monkeypatch.setattr(
        "agent_tools.agent_workspace.components.settings.src.settings.urllib.request.urlopen",
        _fake_urlopen_factory(
            {
                AGENT_WORKSPACE_RELEASES_LATEST_URL: (
                    b"",
                    "https://github.com/svlad-90/agent_tools/releases/tag/v2.1.0",
                ),
                "https://github.com/svlad-90/agent_tools/archive/refs/tags/v2.1.0.tar.gz": tarball,
            }
        ),
    )
    monkeypatch.setattr("agent_tools.agent_workspace.components.settings.src.settings.subprocess.run", fake_run)

    result = run_agent_workspace_update(workspace, python_executable="/missing-python")

    assert result.ok is False
    assert "Latest release: 2.1.0" in result.output
    assert "stdout text" in result.output
    assert "stderr text" in result.output
    assert (workspace / "agent_tools" / "VERSION").read_text(encoding="utf-8") == "2.1.0\n"


def test_run_agent_workspace_update_check_reports_available_updates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "agent_tools").mkdir(parents=True)
    (workspace / "agent_tools" / "VERSION").write_text("2.0.0\n", encoding="utf-8")
    (workspace / "install-agent-tools.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    monkeypatch.setattr(
        "agent_tools.agent_workspace.components.settings.src.settings.urllib.request.urlopen",
        _fake_urlopen_factory(
            {
                AGENT_WORKSPACE_RELEASES_LATEST_URL: (
                    b"",
                    "https://github.com/svlad-90/agent_tools/releases/tag/v2.1.0",
                ),
            }
        ),
    )

    result = run_agent_workspace_update_check(workspace)

    assert result.ok is True
    assert result.update_available is True
    assert result.current_version == "2.0.0"
    assert result.latest_version == "2.1.0"
    assert result.release_url == "https://github.com/svlad-90/agent_tools/releases/tag/v2.1.0"
    assert result.tarball_url == "https://github.com/svlad-90/agent_tools/archive/refs/tags/v2.1.0.tar.gz"
    assert result.commands == (("GET", AGENT_WORKSPACE_RELEASES_LATEST_URL),)


def test_run_agent_workspace_update_check_returns_failed_release_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "agent_tools").mkdir(parents=True)
    (workspace / "install-agent-tools.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    def fake_urlopen(_request: object, **_kwargs: object) -> object:
        raise OSError("network down")

    monkeypatch.setattr(
        "agent_tools.agent_workspace.components.settings.src.settings.urllib.request.urlopen",
        fake_urlopen,
    )

    result = run_agent_workspace_update_check(workspace)

    assert result.ok is False
    assert result.update_available is False
    assert "network down" in result.output


class _FakeResponse:
    def __init__(self, payload: bytes, final_url: str = "") -> None:
        self.payload = payload
        self.final_url = final_url

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload

    def geturl(self) -> str:
        return self.final_url


def _fake_urlopen_factory(payloads: dict[str, bytes | tuple[bytes, str]]) -> object:
    def fake_urlopen(request: object, **_kwargs: object) -> _FakeResponse:
        url = getattr(request, "full_url", request)
        payload = payloads[str(url)]
        if isinstance(payload, tuple):
            return _FakeResponse(payload[0], payload[1])
        return _FakeResponse(payload, str(url))

    return fake_urlopen


def _agent_workspace_release_tarball() -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name, payload in (
            ("release/install-agent-tools.py", b"#!/usr/bin/env python3\n"),
            ("release/agent_tools/VERSION", b"2.1.0\n"),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return output.getvalue()

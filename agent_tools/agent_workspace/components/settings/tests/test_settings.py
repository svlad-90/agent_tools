from __future__ import annotations

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
            "inject_task_context_prompt": False,
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
        "inject_task_context_prompt": False,
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
    }


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
            "inject_task_context_prompt": False,
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
    assert settings.inject_task_context_prompt is False
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
    assert settings.inject_task_context_prompt is True
    assert settings.task_dictionary_auto_discovery is True
    assert settings.task_dictionary_min_occurrences == 1
    assert settings.task_dictionary_min_saving == 0
    assert settings.task_dictionary_min_term_length == 1
    assert settings.task_dictionary_max_term_words == 20
    assert settings.task_dictionary_strip_articles is True
    assert settings.task_dictionary_preview_text == DICTIONARY_PREVIEW_TEXT
    assert len(settings.task_dictionary_preview_text) > 5_000
    assert "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py" in settings.task_dictionary_preview_text
    assert "TASK_CONTEXT.sqlite3" in settings.task_dictionary_preview_text
    assert settings.window_geometry == "1180x760"
    assert settings.main_split_ratio == 0.25
    assert settings.details_split_ratio == 0.25
    assert settings.actions_split_ratio == 0.38


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

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from agent_tools.tools.task_context import DICTIONARY_AUTO_DISCOVERY_DEFAULT
from agent_tools.tools.task_context import DICTIONARY_MAX_TERM_WORDS
from agent_tools.tools.task_context import DICTIONARY_MIN_OCCURRENCES
from agent_tools.tools.task_context import DICTIONARY_MIN_SAVING
from agent_tools.tools.task_context import DICTIONARY_MIN_TERM_LENGTH
from agent_tools.tools.task_context import DICTIONARY_PREVIEW_TEXT
from agent_tools.tools.task_context import DICTIONARY_STRIP_ARTICLES_DEFAULT
from agent_tools.tools.task_context import LEGACY_DICTIONARY_PREVIEW_TEXT
from agent_tools.tools.task_context import TaskDictionaryPolicy


AGENT_WORKSPACE_SETTINGS_FILE = "settings.json"
AGENT_WORKSPACE_THEMES = ("light", "dark")
AGENT_WORKSPACE_LANGUAGES = ("ru", "uk", "en")
AGENT_WORKSPACE_AGENTS = ("codex", "claude")
AGENT_WORKSPACE_DEFAULT_AGENT = "codex"
AGENT_WORKSPACE_DEFAULT_CODEX_MODEL = "gpt-5.5"
AGENT_WORKSPACE_DEFAULT_CODEX_REASONING = "medium"
AGENT_WORKSPACE_DEFAULT_CLAUDE_MODEL = "sonnet"
AGENT_WORKSPACE_DEFAULT_CLAUDE_EFFORT = "medium"
AGENT_WORKSPACE_DEFAULT_CLAUDE_PERMISSION_MODE = "auto"
AGENT_WORKSPACE_CODEX_MODEL_FALLBACKS = (
    "gpt-5.6-sol",
    "gpt-5.6-sol-wm",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-5.5",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.3-codex-spark",
)
AGENT_WORKSPACE_CLAUDE_MODELS = ("sonnet", "opus")
AGENT_WORKSPACE_REASONING_EFFORTS = ("low", "medium", "high", "xhigh", "max")
AGENT_WORKSPACE_AGENT_LABELS = {
    "codex": "Codex",
    "claude": "Claude Code",
}
AGENT_WORKSPACE_AGENT_COMMANDS = {
    "codex": "codex",
    "claude": "claude",
}
AGENT_WORKSPACE_AGENT_INSTALL_COMMANDS = {
    "codex": "npm install -g @openai/codex",
    "claude": "npm install -g @anthropic-ai/claude-code",
}
AGENT_WORKSPACE_GEOMETRY_RE = re.compile(r"^\d+x\d+(?:[+-]\d+[+-]\d+)?$")
TASK_CONTEXT_PROMPT_INJECTION_DEFAULT = True


@dataclass(frozen=True)
class AgentWorkspaceRuntimeSettings:
    text_font_size: int
    button_font_size: int
    theme: str
    language: str
    default_agent: str
    default_codex_model: str
    default_codex_reasoning: str
    default_claude_model: str
    default_claude_effort: str
    inject_task_context_prompt: bool
    task_dictionary_auto_discovery: bool
    task_dictionary_min_occurrences: int
    task_dictionary_min_saving: int
    task_dictionary_min_term_length: int
    task_dictionary_max_term_words: int
    task_dictionary_strip_articles: bool
    task_dictionary_preview_text: str
    window_geometry: str
    main_split_ratio: float
    details_split_ratio: float
    actions_split_ratio: float


@dataclass(frozen=True)
class AgentModelSettings:
    model: str
    reasoning_effort: str


@dataclass(frozen=True)
class AgentModelChoices:
    choices: tuple[str, ...]
    source: str


def agent_workspace_settings_path() -> Path:
    config_root = os.environ.get("XDG_CONFIG_HOME")
    if config_root:
        return Path(config_root) / "agent_tools" / "agent_workspace" / AGENT_WORKSPACE_SETTINGS_FILE
    return Path.home() / ".config" / "agent_tools" / "agent_workspace" / AGENT_WORKSPACE_SETTINGS_FILE


def normalize_agent(agent: object) -> str:
    if isinstance(agent, str) and agent in AGENT_WORKSPACE_AGENTS:
        return agent
    return AGENT_WORKSPACE_DEFAULT_AGENT


def agent_label(agent: str) -> str:
    return AGENT_WORKSPACE_AGENT_LABELS.get(normalize_agent(agent), normalize_agent(agent))


def agent_command_name(agent: str) -> str:
    agent = normalize_agent(agent)
    return AGENT_WORKSPACE_AGENT_COMMANDS.get(agent, agent)


def agent_executable(agent: str) -> str | None:
    command = agent_command_name(agent)
    executable = shutil.which(command)
    if executable:
        return executable
    local_bin = Path.home() / ".local" / "bin" / command
    if local_bin.is_file():
        return str(local_bin)
    return None


def agent_install_command(agent: str) -> str:
    agent = normalize_agent(agent)
    return AGENT_WORKSPACE_AGENT_INSTALL_COMMANDS.get(agent, "")


def codex_model_choices_info(
    cache_path: Path | None = None,
    *,
    use_cli: bool = True,
    timeout: float = 5.0,
) -> AgentModelChoices:
    if use_cli:
        choices = _codex_model_choices_from_cli(timeout=timeout)
        if choices is not None:
            return AgentModelChoices(choices, "Codex CLI: codex debug models")
    path = cache_path or (Path.home() / ".codex" / "models_cache.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AgentModelChoices(AGENT_WORKSPACE_CODEX_MODEL_FALLBACKS, "fallback")
    choices = _model_choices_from_catalog(data)
    if choices is None:
        return AgentModelChoices(AGENT_WORKSPACE_CODEX_MODEL_FALLBACKS, "fallback")
    return AgentModelChoices(choices, f"Codex cache: {path}")


def codex_model_choices(cache_path: Path | None = None) -> tuple[str, ...]:
    return codex_model_choices_info(cache_path, use_cli=cache_path is None).choices


def claude_model_choices_info() -> AgentModelChoices:
    configured = _claude_configured_model_choices()
    if len(configured) > 1:
        return AgentModelChoices(
            _unique_model_choices((*configured, *AGENT_WORKSPACE_CLAUDE_MODELS)),
            "Claude settings",
        )
    if agent_executable("claude") is not None:
        return AgentModelChoices(AGENT_WORKSPACE_CLAUDE_MODELS, "Claude CLI installed")
    return AgentModelChoices(AGENT_WORKSPACE_CLAUDE_MODELS, "fallback")


def claude_model_choices() -> tuple[str, ...]:
    return claude_model_choices_info().choices


def model_choices_with_current(choices: tuple[str, ...], current: str) -> tuple[str, ...]:
    current = current.strip()
    if current and current not in choices:
        return (*choices, current)
    return choices


def agent_workspace_setting_or_default(settings: dict[str, int | float | str | bool], key: str, default: str) -> str:
    value = settings.get(key)
    if not isinstance(value, str):
        return default
    value = value.strip()
    return value or default


def agent_workspace_runtime_settings(
    settings: dict[str, int | float | str | bool],
    *,
    default_font_size: int,
    default_language: str = "ru",
    default_geometry: str = "1180x760",
) -> AgentWorkspaceRuntimeSettings:
    return AgentWorkspaceRuntimeSettings(
        text_font_size=_int_setting(settings, "text_font_size", default_font_size),
        button_font_size=_int_setting(settings, "button_font_size", default_font_size),
        theme=_choice_setting(settings, "theme", AGENT_WORKSPACE_THEMES, "light"),
        language=_choice_setting(settings, "language", AGENT_WORKSPACE_LANGUAGES, default_language),
        default_agent=normalize_agent(settings.get("default_agent", AGENT_WORKSPACE_DEFAULT_AGENT)),
        default_codex_model=agent_workspace_setting_or_default(
            settings, "default_codex_model", AGENT_WORKSPACE_DEFAULT_CODEX_MODEL
        ),
        default_codex_reasoning=agent_workspace_setting_or_default(
            settings, "default_codex_reasoning", AGENT_WORKSPACE_DEFAULT_CODEX_REASONING
        ),
        default_claude_model=agent_workspace_setting_or_default(
            settings, "default_claude_model", AGENT_WORKSPACE_DEFAULT_CLAUDE_MODEL
        ),
        default_claude_effort=agent_workspace_setting_or_default(
            settings, "default_claude_effort", AGENT_WORKSPACE_DEFAULT_CLAUDE_EFFORT
        ),
        inject_task_context_prompt=_bool_setting(
            settings,
            "inject_task_context_prompt",
            TASK_CONTEXT_PROMPT_INJECTION_DEFAULT,
        ),
        task_dictionary_auto_discovery=_bool_setting(
            settings,
            "task_dictionary_auto_discovery",
            DICTIONARY_AUTO_DISCOVERY_DEFAULT,
        ),
        task_dictionary_min_occurrences=_int_range_setting(
            settings,
            "task_dictionary_min_occurrences",
            DICTIONARY_MIN_OCCURRENCES,
            1,
            20,
        ),
        task_dictionary_min_saving=_int_range_setting(
            settings,
            "task_dictionary_min_saving",
            DICTIONARY_MIN_SAVING,
            0,
            10_000,
        ),
        task_dictionary_min_term_length=_int_range_setting(
            settings,
            "task_dictionary_min_term_length",
            DICTIONARY_MIN_TERM_LENGTH,
            1,
            200,
        ),
        task_dictionary_max_term_words=_int_range_setting(
            settings,
            "task_dictionary_max_term_words",
            DICTIONARY_MAX_TERM_WORDS,
            1,
            20,
        ),
        task_dictionary_strip_articles=_bool_setting(
            settings,
            "task_dictionary_strip_articles",
            DICTIONARY_STRIP_ARTICLES_DEFAULT,
        ),
        task_dictionary_preview_text=_task_dictionary_preview_text_setting(
            settings,
            "task_dictionary_preview_text",
        ),
        window_geometry=_str_setting(settings, "geometry", default_geometry),
        main_split_ratio=_float_setting(settings, "main_split_ratio", 0.25),
        details_split_ratio=_float_setting(settings, "details_split_ratio", 0.25),
        actions_split_ratio=_float_setting(settings, "actions_split_ratio", 0.38),
    )


def task_dictionary_policy_from_runtime_settings(settings: AgentWorkspaceRuntimeSettings) -> TaskDictionaryPolicy:
    return TaskDictionaryPolicy(
        auto_discovery=settings.task_dictionary_auto_discovery,
        min_occurrences=settings.task_dictionary_min_occurrences,
        min_saving=settings.task_dictionary_min_saving,
        min_term_length=settings.task_dictionary_min_term_length,
        max_term_words=settings.task_dictionary_max_term_words,
        strip_articles=settings.task_dictionary_strip_articles,
    )


def ai_agent_model_settings(
    agent: str,
    *,
    codex_model: str,
    codex_reasoning: str,
    claude_model: str,
    claude_effort: str,
) -> AgentModelSettings:
    if normalize_agent(agent) == "claude":
        return AgentModelSettings(
            model=claude_model,
            reasoning_effort=claude_effort,
        )
    return AgentModelSettings(
        model=codex_model,
        reasoning_effort=codex_reasoning,
    )


def load_agent_workspace_settings(path: Path | None = None) -> dict[str, int | float | str | bool]:
    settings_path = path or agent_workspace_settings_path()
    if not settings_path.is_file():
        return {}
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    settings: dict[str, int | float | str | bool] = {}
    text_font_size = data.get("text_font_size", data.get("font_size"))
    button_font_size = data.get("button_font_size")
    theme = data.get("theme")
    language = data.get("language")
    geometry = data.get("geometry")
    default_agent = data.get("default_agent")
    default_codex_model = data.get("default_codex_model")
    default_codex_reasoning = data.get("default_codex_reasoning")
    default_claude_model = data.get("default_claude_model")
    default_claude_effort = data.get("default_claude_effort")
    inject_task_context_prompt = data.get("inject_task_context_prompt")
    task_dictionary_auto_discovery = data.get("task_dictionary_auto_discovery")
    task_dictionary_min_occurrences = data.get("task_dictionary_min_occurrences")
    task_dictionary_min_saving = data.get("task_dictionary_min_saving")
    task_dictionary_min_term_length = data.get("task_dictionary_min_term_length")
    task_dictionary_max_term_words = data.get("task_dictionary_max_term_words")
    task_dictionary_strip_articles = data.get("task_dictionary_strip_articles")
    task_dictionary_preview_text = data.get("task_dictionary_preview_text")
    main_split_ratio = data.get("main_split_ratio")
    details_split_ratio = data.get("details_split_ratio")
    actions_split_ratio = data.get("actions_split_ratio")
    if isinstance(text_font_size, int):
        settings["text_font_size"] = max(8, min(28, text_font_size))
    if isinstance(button_font_size, int):
        settings["button_font_size"] = max(8, min(28, button_font_size))
    if isinstance(theme, str) and theme in AGENT_WORKSPACE_THEMES:
        settings["theme"] = theme
    if isinstance(language, str) and language in AGENT_WORKSPACE_LANGUAGES:
        settings["language"] = language
    if isinstance(geometry, str) and AGENT_WORKSPACE_GEOMETRY_RE.fullmatch(geometry):
        settings["geometry"] = geometry
    if isinstance(default_agent, str) and default_agent in AGENT_WORKSPACE_AGENTS:
        settings["default_agent"] = default_agent
    if isinstance(default_codex_model, str) and default_codex_model.strip():
        settings["default_codex_model"] = default_codex_model.strip()
    if isinstance(default_codex_reasoning, str) and default_codex_reasoning in AGENT_WORKSPACE_REASONING_EFFORTS:
        settings["default_codex_reasoning"] = default_codex_reasoning
    if isinstance(default_claude_model, str) and default_claude_model.strip():
        settings["default_claude_model"] = default_claude_model.strip()
    if isinstance(default_claude_effort, str) and default_claude_effort in AGENT_WORKSPACE_REASONING_EFFORTS:
        settings["default_claude_effort"] = default_claude_effort
    if isinstance(inject_task_context_prompt, bool):
        settings["inject_task_context_prompt"] = inject_task_context_prompt
    if isinstance(task_dictionary_auto_discovery, bool):
        settings["task_dictionary_auto_discovery"] = task_dictionary_auto_discovery
    for key, value, minimum, maximum in (
        ("task_dictionary_min_occurrences", task_dictionary_min_occurrences, 1, 20),
        ("task_dictionary_min_saving", task_dictionary_min_saving, 0, 10_000),
        ("task_dictionary_min_term_length", task_dictionary_min_term_length, 1, 200),
        ("task_dictionary_max_term_words", task_dictionary_max_term_words, 1, 20),
    ):
        if isinstance(value, int) and not isinstance(value, bool):
            settings[key] = max(minimum, min(maximum, value))
    if isinstance(task_dictionary_strip_articles, bool):
        settings["task_dictionary_strip_articles"] = task_dictionary_strip_articles
    if isinstance(task_dictionary_preview_text, str):
        settings["task_dictionary_preview_text"] = task_dictionary_preview_text
    for key, value in (
        ("main_split_ratio", main_split_ratio),
        ("details_split_ratio", details_split_ratio),
        ("actions_split_ratio", actions_split_ratio),
    ):
        if isinstance(value, int | float) and 0.05 <= float(value) <= 0.95:
            settings[key] = float(value)
    return settings


def save_agent_workspace_settings(settings: dict[str, int | float | str | bool], path: Path | None = None) -> None:
    settings_path = path or agent_workspace_settings_path()
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        return


def _codex_model_choices_from_cli(*, timeout: float) -> tuple[str, ...] | None:
    executable = agent_executable("codex")
    if executable is None:
        return None
    try:
        result = subprocess.run(
            [executable, "debug", "models"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    data = _json_object_from_output(f"{result.stdout}\n{result.stderr}")
    if data is None:
        return None
    return _model_choices_from_catalog(data)


def _model_choices_from_catalog(data: object) -> tuple[str, ...] | None:
    if not isinstance(data, dict):
        return None
    models = data.get("models")
    if not isinstance(models, list):
        return None
    choices: list[str] = []
    for model in models:
        if not isinstance(model, dict):
            continue
        slug = model.get("slug")
        if isinstance(slug, str) and slug and slug not in choices:
            choices.append(slug)
    if not choices:
        return None
    return tuple(choices)


def _json_object_from_output(output: str) -> object | None:
    start = output.find("{")
    end = output.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        return json.loads(output[start : end + 1])
    except json.JSONDecodeError:
        return None


def _claude_configured_model_choices() -> tuple[str, ...]:
    values: list[str] = []
    for path in (Path.home() / ".claude" / "settings.json", Path.home() / ".claude" / "remote-settings.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        values.extend(_model_strings_from_settings(data))
    return _unique_model_choices(tuple(values))


def _model_strings_from_settings(data: object) -> tuple[str, ...]:
    values: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(key, str) and "model" in key.casefold() and isinstance(value, str):
                normalized = value.strip()
                if normalized:
                    values.append(normalized)
            values.extend(_model_strings_from_settings(value))
    elif isinstance(data, list):
        for item in data:
            values.extend(_model_strings_from_settings(item))
    return tuple(values)


def _unique_model_choices(values: tuple[str, ...]) -> tuple[str, ...]:
    choices: list[str] = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in choices:
            choices.append(normalized)
    return tuple(choices)


def _task_dictionary_preview_text_setting(settings: dict[str, int | float | str | bool], key: str) -> str:
    value = settings.get(key)
    if not isinstance(value, str):
        return DICTIONARY_PREVIEW_TEXT
    value = value.strip()
    if not value or _is_legacy_dictionary_preview_text(value):
        return DICTIONARY_PREVIEW_TEXT
    return value


def _is_legacy_dictionary_preview_text(value: str) -> bool:
    return (
        len(value) < 1_000
        and value.startswith("Agent Workspace renders TASK_CONTEXT.sqlite3 entries.")
        and "validates Agent Workspace behavior" in value
    ) or value == LEGACY_DICTIONARY_PREVIEW_TEXT


def _int_setting(settings: dict[str, int | float | str | bool], key: str, default: int) -> int:
    value = settings.get(key)
    if isinstance(value, int):
        return value
    return default


def _int_range_setting(
    settings: dict[str, int | float | str | bool],
    key: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    value = _int_setting(settings, key, default)
    return max(minimum, min(maximum, value))


def _float_setting(settings: dict[str, int | float | str | bool], key: str, default: float) -> float:
    value = settings.get(key)
    if isinstance(value, int | float):
        ratio = float(value)
    elif isinstance(value, str):
        try:
            ratio = float(value)
        except ValueError:
            return default
    else:
        return default
    if 0.05 <= ratio <= 0.95:
        return ratio
    return default


def _choice_setting(
    settings: dict[str, int | float | str | bool],
    key: str,
    choices: tuple[str, ...],
    default: str,
) -> str:
    value = settings.get(key)
    if isinstance(value, str) and value in choices:
        return value
    return default


def _str_setting(settings: dict[str, int | float | str | bool], key: str, default: str) -> str:
    value = settings.get(key)
    if isinstance(value, str):
        return value
    return default


def _bool_setting(settings: dict[str, int | float | str | bool], key: str, default: bool) -> bool:
    value = settings.get(key)
    return value if isinstance(value, bool) else default

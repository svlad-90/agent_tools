from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

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
AGENT_WORKSPACE_DEFAULT_CODEX_ANIMATIONS_ENABLED = False
AGENT_WORKSPACE_DEFAULT_CLAUDE_ANIMATIONS_ENABLED = False
AGENT_WORKSPACE_DEFAULT_LIMITED_BASH_OUTPUT_TOKENS = 2_000
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
AgentWorkspaceSettingValue = int | float | str | bool | list[str]
AGENT_WORKSPACE_RELEASES_API = "https://api.github.com/repos/svlad-90/agent_tools/releases/latest"


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
    codex_animations_enabled: bool
    claude_animations_enabled: bool
    limited_bash_output_tokens: int
    system_prompt: str
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


@dataclass(frozen=True)
class AgentWorkspaceUpdateResult:
    commands: tuple[tuple[str, ...], ...]
    returncode: int
    output: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass(frozen=True)
class AgentWorkspaceUpdateCheckResult:
    commands: tuple[tuple[str, ...], ...]
    returncode: int
    output: str
    current_version: str = ""
    latest_version: str = ""
    release_url: str = ""
    tarball_url: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def update_available(self) -> bool:
        return self.ok and _version_key(self.latest_version) > _version_key(self.current_version)


def agent_workspace_settings_path() -> Path:
    config_root = os.environ.get("XDG_CONFIG_HOME")
    if config_root:
        return Path(config_root) / "agent_tools" / "agent_workspace" / AGENT_WORKSPACE_SETTINGS_FILE
    return Path.home() / ".config" / "agent_tools" / "agent_workspace" / AGENT_WORKSPACE_SETTINGS_FILE


def agent_workspace_root(start: Path | None = None) -> Path:
    path = (start or Path(__file__)).resolve()
    for candidate in (path, *path.parents):
        if (candidate / "install-agent-tools.py").is_file() and (candidate / "agent_tools").is_dir():
            return candidate
    raise RuntimeError(f"cannot resolve Agent Workspace root from {path}")


def agent_workspace_install_root(start: Path | None = None) -> Path:
    return agent_workspace_root(start)


def agent_workspace_update_commands(
    workspace: Path | None = None,
    *,
    python_executable: str | None = None,
) -> tuple[tuple[str, ...], ...]:
    root = agent_workspace_install_root(workspace) if workspace is not None else agent_workspace_install_root()
    python = python_executable or sys.executable
    return (
        (
            python,
            str(root / "install-agent-tools.py"),
            "--non-interactive",
            "--skip-system-deps",
            "--recreate-venv-if-broken",
        ),
    )


def run_agent_workspace_update_check(
    install_root: Path | None = None,
    *,
    timeout: float | None = None,
) -> AgentWorkspaceUpdateCheckResult:
    root = agent_workspace_install_root(install_root) if install_root is not None else agent_workspace_install_root()
    current_version = _agent_workspace_current_version(root)
    commands = (("GET", AGENT_WORKSPACE_RELEASES_API),)
    output_parts: list[str] = []
    try:
        payload = _read_release_json(timeout=timeout)
    except TimeoutError:
        output_parts.append(f"Timed out after {timeout} seconds.")
        return AgentWorkspaceUpdateCheckResult(commands, 124, "\n".join(output_parts).rstrip() + "\n", current_version)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        output_parts.append(f"{type(error).__name__}: {error}")
        return AgentWorkspaceUpdateCheckResult(commands, 1, "\n".join(output_parts).rstrip() + "\n", current_version)
    latest_version = _release_version(payload.get("tag_name"))
    release_url = _string_value(payload.get("html_url"))
    tarball_url = _string_value(payload.get("tarball_url"))
    if not latest_version or not tarball_url:
        output_parts.append("Latest GitHub release does not contain tag_name and tarball_url.")
        return AgentWorkspaceUpdateCheckResult(commands, 1, "\n".join(output_parts).rstrip() + "\n", current_version)
    output_parts.append(f"Current version: {current_version}")
    output_parts.append(f"Latest release: {latest_version}")
    return AgentWorkspaceUpdateCheckResult(
        commands,
        0,
        "\n".join(output_parts).rstrip() + "\n",
        current_version,
        latest_version,
        release_url,
        tarball_url,
    )


def run_agent_workspace_update(
    install_root: Path | None = None,
    *,
    python_executable: str | None = None,
    timeout: float | None = None,
) -> AgentWorkspaceUpdateResult:
    root = agent_workspace_install_root(install_root) if install_root is not None else agent_workspace_install_root()
    check = run_agent_workspace_update_check(root, timeout=timeout)
    if not check.ok:
        return AgentWorkspaceUpdateResult(check.commands, check.returncode, check.output)
    if not check.update_available:
        return AgentWorkspaceUpdateResult(check.commands, 0, check.output + "No release update available.\n")
    commands = agent_workspace_update_commands(root, python_executable=python_executable)
    output_parts: list[str] = []
    output_parts.append(check.output.rstrip())
    try:
        with tempfile.TemporaryDirectory(prefix="agent-workspace-update-") as temp_dir:
            release_source = _download_and_extract_release(check.tarball_url, Path(temp_dir), timeout=timeout)
            _copy_release_tree(release_source, root)
    except (OSError, tarfile.TarError, ValueError) as error:
        output_parts.append(f"{type(error).__name__}: {error}")
        return AgentWorkspaceUpdateResult(
            (("download", check.tarball_url), *commands),
            1,
            "\n".join(output_parts).rstrip() + "\n",
        )
    env = os.environ.copy()
    current_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(root) if not current_pythonpath else f"{root}{os.pathsep}{current_pythonpath}"
    for command in commands:
        output_parts.append("$ " + " ".join(command))
        try:
            completed = subprocess.run(
                command,
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as error:
            partial = (error.stdout or "") + (error.stderr or "")
            if partial:
                output_parts.append(partial)
            output_parts.append(f"Timed out after {timeout} seconds.")
            return AgentWorkspaceUpdateResult(commands, 124, "\n".join(output_parts).rstrip() + "\n")
        if completed.stdout:
            output_parts.append(completed.stdout.rstrip())
        if completed.stderr:
            output_parts.append(completed.stderr.rstrip())
        if completed.returncode != 0:
            return AgentWorkspaceUpdateResult(commands, completed.returncode, "\n".join(output_parts).rstrip() + "\n")
    return AgentWorkspaceUpdateResult((("download", check.tarball_url), *commands), 0, "\n".join(output_parts).rstrip() + "\n")


def _read_release_json(*, timeout: float | None) -> dict[str, object]:
    request = urllib.request.Request(
        AGENT_WORKSPACE_RELEASES_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "agent-workspace-updater",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("GitHub release response is not a JSON object")
    return data


def _agent_workspace_current_version(root: Path) -> str:
    version_file = root / "agent_tools" / "VERSION"
    if version_file.is_file():
        version = version_file.read_text(encoding="utf-8").strip()
        if version:
            return _release_version(version)
    git = shutil.which("git")
    if git is not None and (root / ".git").exists():
        completed = subprocess.run(
            (git, "-C", str(root), "describe", "--tags", "--abbrev=0"),
            text=True,
            capture_output=True,
            timeout=5,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            return _release_version(completed.stdout.strip())
    return "0.0.0"


def _download_and_extract_release(tarball_url: str, temp_dir: Path, *, timeout: float | None) -> Path:
    archive_path = temp_dir / "release.tar.gz"
    request = urllib.request.Request(tarball_url, headers={"User-Agent": "agent-workspace-updater"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        archive_path.write_bytes(response.read())
    extract_dir = temp_dir / "extract"
    extract_dir.mkdir()
    with tarfile.open(archive_path, "r:*") as archive:
        _safe_extract_tar(archive, extract_dir)
    children = [path for path in extract_dir.iterdir() if path.is_dir()]
    if len(children) != 1:
        raise ValueError("release archive must contain one top-level directory")
    release_source = children[0]
    if not (release_source / "install-agent-tools.py").is_file() or not (release_source / "agent_tools").is_dir():
        raise ValueError("release archive does not look like Agent Workspace")
    return release_source


def _safe_extract_tar(archive: tarfile.TarFile, target: Path) -> None:
    target_root = target.resolve()
    for member in archive.getmembers():
        if member.issym() or member.islnk():
            raise ValueError(f"links are not allowed in release archive: {member.name}")
        member_target = (target / member.name).resolve()
        try:
            member_target.relative_to(target_root)
        except ValueError as error:
            raise ValueError(f"unsafe path in release archive: {member.name}") from error
    archive.extractall(target)


def _copy_release_tree(source: Path, target: Path) -> None:
    for item in source.iterdir():
        if item.name == ".git":
            continue
        destination = target / item.name
        if item.is_dir():
            shutil.copytree(item, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(item, destination)


def _release_version(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().removeprefix("v")


def _string_value(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _version_key(version: str) -> tuple[int, ...]:
    numbers = []
    for part in version.split("."):
        if not part.isdigit():
            break
        numbers.append(int(part))
    return tuple(numbers)


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
        codex_animations_enabled=_bool_setting(
            settings,
            "codex_animations_enabled",
            AGENT_WORKSPACE_DEFAULT_CODEX_ANIMATIONS_ENABLED,
        ),
        claude_animations_enabled=_bool_setting(
            settings,
            "claude_animations_enabled",
            AGENT_WORKSPACE_DEFAULT_CLAUDE_ANIMATIONS_ENABLED,
        ),
        limited_bash_output_tokens=_int_range_setting(
            settings,
            "limited_bash_output_tokens",
            AGENT_WORKSPACE_DEFAULT_LIMITED_BASH_OUTPUT_TOKENS,
            100,
            200_000,
        ),
        system_prompt=_str_setting(settings, "system_prompt", ""),
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


def load_agent_workspace_settings(path: Path | None = None) -> dict[str, AgentWorkspaceSettingValue]:
    settings_path = path or agent_workspace_settings_path()
    if not settings_path.is_file():
        return {}
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    settings: dict[str, AgentWorkspaceSettingValue] = {}
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
    codex_animations_enabled = data.get("codex_animations_enabled")
    claude_animations_enabled = data.get("claude_animations_enabled")
    limited_bash_output_tokens = data.get("limited_bash_output_tokens")
    system_prompt = data.get("system_prompt")
    if not isinstance(limited_bash_output_tokens, int) or isinstance(limited_bash_output_tokens, bool):
        legacy_chars = data.get("limited_bash_output_chars")
        if isinstance(legacy_chars, int) and not isinstance(legacy_chars, bool):
            limited_bash_output_tokens = (legacy_chars + 3) // 4
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
    last_workspace = data.get("last_workspace")
    recent_workspaces = data.get("recent_workspaces")
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
    if isinstance(codex_animations_enabled, bool):
        settings["codex_animations_enabled"] = codex_animations_enabled
    if isinstance(claude_animations_enabled, bool):
        settings["claude_animations_enabled"] = claude_animations_enabled
    if isinstance(system_prompt, str):
        settings["system_prompt"] = system_prompt
    if isinstance(inject_task_context_prompt, bool):
        settings["inject_task_context_prompt"] = inject_task_context_prompt
    if isinstance(task_dictionary_auto_discovery, bool):
        settings["task_dictionary_auto_discovery"] = task_dictionary_auto_discovery
    for key, value, minimum, maximum in (
        ("task_dictionary_min_occurrences", task_dictionary_min_occurrences, 1, 20),
        ("task_dictionary_min_saving", task_dictionary_min_saving, 0, 10_000),
        ("task_dictionary_min_term_length", task_dictionary_min_term_length, 1, 200),
        ("task_dictionary_max_term_words", task_dictionary_max_term_words, 1, 20),
        ("limited_bash_output_tokens", limited_bash_output_tokens, 100, 200_000),
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
    if isinstance(last_workspace, str) and last_workspace.strip():
        settings["last_workspace"] = last_workspace.strip()
    if isinstance(recent_workspaces, list):
        normalized_recent = []
        seen = set()
        for item in recent_workspaces:
            if isinstance(item, str) and item.strip() and item not in seen:
                normalized_recent.append(item.strip())
                seen.add(item)
        if normalized_recent:
            settings["recent_workspaces"] = normalized_recent[:10]
    return settings


def save_agent_workspace_settings(settings: dict[str, AgentWorkspaceSettingValue], path: Path | None = None) -> None:
    settings_path = path or agent_workspace_settings_path()
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        return


def remember_agent_workspace(workspace: Path, path: Path | None = None) -> dict[str, AgentWorkspaceSettingValue]:
    root = str(workspace.resolve())
    settings = load_agent_workspace_settings(path)
    recent = [root]
    existing_recent = settings.get("recent_workspaces")
    if isinstance(existing_recent, list):
        for item in existing_recent:
            if isinstance(item, str) and item != root:
                recent.append(item)
    previous_last = settings.get("last_workspace")
    if isinstance(previous_last, str) and previous_last != root:
        recent.append(previous_last)
    normalized_recent = []
    seen = set()
    for item in recent:
        if item and item not in seen:
            normalized_recent.append(item)
            seen.add(item)
    settings["last_workspace"] = root
    settings["recent_workspaces"] = normalized_recent[:10]
    save_agent_workspace_settings(settings, path)
    return settings


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

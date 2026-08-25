# Agent Workspace Settings Component

Owns global Agent Workspace settings, agent defaults, model catalog discovery,
and runtime settings normalization.

Public callers import from `components.settings.api`. Implementation details
such as JSON parsing, CLI model discovery, and value sanitizers stay in `src`.

Runtime settings include:

- theme, language, font sizes, and window geometry;
- the default agent and per-agent model/reasoning defaults;
- separate animation toggles for Codex and Claude Code, disabled by default;
- the Bash output guard token limit, defaulting to 2000 estimated tokens;
- task dictionary discovery thresholds and task context injection behavior.

The Bash output limit is stored as `limited_bash_output_tokens`. Older
`limited_bash_output_chars` values are migrated to an estimated token value
when settings are loaded.

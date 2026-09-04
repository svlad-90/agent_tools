# Agent Workspace Settings Component

Owns global Agent Workspace settings, agent defaults, model catalog discovery,
and runtime settings normalization.

Public callers import from `components.settings.api`. Implementation details
such as JSON parsing, CLI model discovery, and value sanitizers stay in `src`.

Runtime settings include:

- theme, language, font sizes, and window geometry;
- the default agent and per-agent model/reasoning defaults;
- separate animation toggles for Codex and Claude Code, disabled by default;
- Bash output guard budgets: 2000 head tokens, 2000 tail tokens, a 30-second
  heartbeat interval, and a 1000-token total heartbeat detail budget;
- enabled Agent Workspace MCP tool groups and the trusted-server toggle for
  Codex/Claude MCP approval settings;
- task dictionary discovery thresholds and task context injection behavior.

The split Bash output budgets are stored as `limited_bash_head_tokens`,
`limited_bash_tail_tokens`, `limited_bash_heartbeat_seconds`, and
`limited_bash_heartbeat_tokens`. The older `limited_bash_output_tokens` key is
kept as a compatibility fallback for head/tail defaults. Older
`limited_bash_output_chars` values are migrated to an estimated token value
when settings are loaded.

The MCP trusted-server toggle writes the documented Codex and Claude Code
approval settings only when the checkbox changes. Tool group selection is stored
as regular Agent Workspace settings and is passed to new agent sessions by
filtering the workspace MCP server's advertised tools.
MCP tool group labels and tooltips are localized through the GTK translation
catalog; the workspace MCP component keeps English fallback metadata with the
group definitions.

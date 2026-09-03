# Agent Workspace

`agent_workspace` is the local desktop dashboard for workspace tasks. It is
named around the workspace rather than Codex because the same task layout can be
used by Codex, Claude Code, plain shell sessions, or another local agent.

Launch from the workspace root on Linux:

```sh
./agent-workspace.sh
```

Launch the browser UI explicitly:

```sh
./agent-workspace-web.sh
```

On macOS, use `agent-workspace.command` or `agent-workspace-web.command`.
On Windows, use `agent-workspace.cmd` or `agent-workspace-web.cmd`. The macOS
and Windows default launchers start the browser UI because the embedded
GTK/VTE and Tk terminal backends are POSIX/Linux-oriented.

Install or refresh the launcher, Python dependencies, desktop entry, and
workspace-local agent skill mirrors with:

```sh
python3 install-agent-tools.py
```

When launched from an interactive terminal without flags, the installer opens a
console wizard for UI selection, common system tools, Docker support, and
developer/test dependencies. GTK selection installs GTK/VTE packages through
the host package manager and may ask for `sudo`.

For automation, keep using explicit flags such as
`python3 install-agent-tools.py --non-interactive --skip-system-deps --dev`.
On Linux, the `agent-workspace` default entry point tries GTK, then web, then
Tk. On macOS and Windows, it uses web directly. The `agent-workspace-web` entry
points always skip desktop backend probing and start the browser UI.

Main capabilities:

- browse task directories under `tasks/`;
- render the task goal slot from `TASK_CONTEXT.sqlite3`;
- render current task context slots with category filters;
- run compact `task_check` checks through the built-in action runner;
- load task-declared actions from `TASK_ACTIONS.json` and run them in the
  active task terminal;
- manage per-task terminal tabs and one interactive AI agent terminal per task;
- open task artifacts from `report/`, `report/diff/`, and `report/puml/`;
- filter task artifacts by extension and path/name text;
- remove artifact files through guarded confirmation dialogs;
- persist theme, language, font sizes, window geometry, the default AI agent,
  each task's selected AI agent, and the task-local AI agent session to resume.
- show AI harness debug events for the selected task/session, including hook
  checkpoints, tool start/finish events, context injection points, Stop gates,
  and compact gates.
- collect GTK profiling counters from Settings > Profiling when diagnosing
  redraw, motion, size, and terminal event overhead.

If the selected AI agent command is missing from `PATH`, the GUI shows an
installation prompt instead of opening a broken terminal. Switching a task from
one running AI agent to another asks for confirmation because the old agent
session has to be closed before the new one starts with the same task context.
Closing the Agent Workspace window also asks for confirmation while any AI
agent sessions are still running.
When a task's AI agent is launched again after the window was restarted, Codex
resumes only a saved session id that can be matched to that task. If no
task-bound session id is known, Codex starts a fresh session with the selected
task context instead of resuming an unrelated global latest session. Claude
Code launches with the task context prompt, but Agent Workspace does not invent
Claude conversation ids; without a real Claude Code conversation id, the UI
keeps the action as a new launch instead of showing a restore action.
The settings dialog can also set default models and reasoning effort for each
agent. Model fields are combo boxes: Codex choices are loaded quickly from
cache/fallback data and refreshed asynchronously from the local Codex CLI;
Claude Code choices use configured local aliases plus `sonnet` and `opus`.
Codex launches use `--model` and `-c model_reasoning_effort="..."`; Claude Code launches use
`--permission-mode auto`, `--model`, and `--effort`. Empty model and effort
values leave the agent CLI defaults in control. Initial defaults are Codex
`gpt-5.5` with `medium` reasoning and Claude Code `sonnet` with `medium`
effort, so new Agent Workspace installs do not silently launch Claude's
highest-cost default model.
Agent animations are disabled by default and can be enabled separately for
Codex and Claude Code. Codex launches always keep `tui.disable_mouse_capture`
enabled; Claude Code keeps its normal mouse support so terminal scrollback
continues to work. Both Codex and Claude Code terminals use the same GTK mouse
proxy around the embedded VTE widget to reduce passive pointer redraw overhead.
The Bash output token limit setting controls hook-driven command output
guarding for both agents. The default limit is 2000 estimated tokens. When a
Bash command exceeds that limit, Agent Workspace returns a short first/last
line preview and guidance to the agent while saving the complete stdout,
stderr, and metadata under the task's `report/logs/limited-bash/` directory.
Agent Workspace also provides a single workspace MCP server for agent-facing
tools. It runs over newline-delimited stdio JSON-RPC and exports tools from a
central registry instead of requiring one MCP server per CLI:

```sh
python -m agent_tools.agent_workspace.components.workspace_mcp --workspace /path/to/workspace
```

Agents should treat this server as the first-choice interface for workspace
utilities when an equivalent MCP tool is available. The CLI modules remain the
implementation layer and fallback path for older clients, shell composition,
build commands, PAF scenarios, and direct human use. Current MCP tool groups
include compact search (`agent_search_*`), Python maps and guarded edits
(`code_map_*`), C/C++ structural and build-backed maps (`cpp_light_*` and
`cpp_code_map_*`), YAML maps and edits (`yaml_map_*`), diff reports
(`diff_report_*`), task context and repo registry (`task_context_*` and
`repo_registry_*`), task actualization (`task_actualize`), task action editing
(`task_actions_*`), commit message formatting (`commit_msg_format`), push
validation (`push_guard_*`), workspace validation (`workspace_validate`,
`validate_changed`, `validate_task`, `workspace_validation_policy`, and
`workspace_validation_status`), and Yocto diagnostics (`yocto_diag_*`). Active
MCP clients may need to be restarted after an Agent Workspace upgrade so they
reload the updated tool schema. Rule synchronization and workspace knowledge
remain file/CLI infrastructure rather than agent-facing MCP tools.
The Settings > MCP tab can enable or disable these tool groups for newly
started agent sessions. The same tab can mark the workspace MCP server as
trusted by writing Codex `default_tools_approval_mode = "approve"` for
`agent_tools_workspace` and Claude Code `mcp__agent-tools__*` allow settings;
clearing the checkbox reverts those approval entries.

The reset-session button forgets only the selected task's selected AI-agent
session in `.agent-workspace-state.json`; it does not delete the underlying
Codex or Claude Code conversation data, and it does not affect another agent
type saved for the same task.
The Actions view remembers the selected console page per task. Returning from
Details or Artifacts restores the previous AI-agent or shell tab; on first
task setup the AI-agent tab is shown by default while a shell tab is still
created for quick manual commands.
Agent Workspace launches Codex and Claude Code with the `harness_adapter`
component configured as their hook bridge. The launch prompt is intentionally
small: it identifies the task and tells the agent that workspace policy is
delivered through hooks. The hook bridge handles session start, user prompt
events, tool start/finish events, Stop gates, compact checkpoints, and task
context injection at session start. Bash tool calls are wrapped by
`limited_bash` before execution so oversized output does not flood the model
context. The pre-commit and pre-push hooks run task_check for repositories
inside `tasks/<task>/` and block when it reports task workflow errors.
The AI status column uses these symbols: `●` means an agent session is open or
restored and idle, `▶` means a user prompt was received, `⚙` means a tool is
running, `▷` means the tool completed and the agent can continue, `○` means
the agent was interrupted manually, `Ⅱ` means a saved session can be resumed,
`□` means no saved session exists, and `×` means another window owns the
active agent process for that task.
Task actions are declared by writing `TASK_ACTIONS.json` at the task root. The
GUI watches that file and refreshes its action buttons when it changes.
Task actions launched from the GUI set `PAF_HIDE_TASK_ENV=1`, so PAF does not
dump the full parameter environment into the task console.
Actions may also declare task-local `parameter_types`, `parameter_sets`,
`global_parameters`, and `shortcuts`. A base action owns the command, parameter
types own reusable field structures, parameter sets own reusable values such as
board IPs or image paths, and shortcuts are user-facing buttons that bind a
base action to a frequently used parameter combination. Action parameters
reference a reusable type with `{"name": "...", "type": "..."}`; the type
declares the backing parameter set via `{"set": "...", "fields": {...}}`.
Parameters that should be shared across actions add `"global": "<name>"`, and
the selected value lives under top-level `global_parameters`. The GTK UI shows
only the shortcuts for the currently selected base action; global parameters
are rendered separately and affect every action that opts into the same global
parameter. Actions, action parameters, global parameters, and per-action
shortcuts can be reordered from their context menus.
Built-in field types are `string`, `file`, and `folder`; custom enum field
types are declared under `field_types` with `{"type": "enum", "values": [...]}`.
Enum fields render as combo boxes. File and folder fields render as editable
paths with a GUI browse button.
New action GUI labels should use string IDs in `UI_STRINGS` instead of inline
literals, with English as the fallback language and Russian/Ukrainian entries
added for visible text.

Built-in action buttons call `python -m agent_tools.agent_workspace.actions`
instead of keeping the action implementation in the already-running GUI
process. After a GUI version with this runner is started, changes to built-in
action implementation are picked up by the next click without restarting the
window.

## Component Boundary

New Agent Workspace code should use component API modules under
`components/<component>/api`. Component implementation lives under
`components/<component>/src`, and component notes live under
`components/<component>/docs`. Code outside a component must not import another
component's `src` package directly.

The component set includes task catalog/context/actions/sessions, artifacts,
commands, settings, localization, markdown, agent runtime/status,
harness_adapter, process runtime, console output, GTK desktop, Tk frontend,
VTE terminal, web frontend, and workspace service. Root modules are reserved
for package entrypoints, installation integration, and launcher code.

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

The installer does not pull GTK/VTE by default. Use
`python3 install-agent-tools.py --gui` only when the legacy GTK UI is needed.
On Linux, the `agent-workspace` default entry point tries GTK, then web, then
Tk. On macOS and Windows, it uses web directly. The `agent-workspace-web`
entry points always skip desktop backend probing and start the browser UI.

Main capabilities:

- browse task directories under `tasks/`;
- render the task goal slot from `TASK_CONTEXT.sqlite3`;
- render current task context slots with category filters;
- run compact `task_check` checks through the built-in action runner;
- load task-declared actions from `TASK_ACTIONS.json` and run them in the
  active task terminal;
- manage per-task terminal tabs and one interactive AI agent terminal per task;
- open task artifacts from `report/`, `report/diff/`, and `report/puml/`;
- remove artifact files through guarded confirmation dialogs;
- persist theme, language, font sizes, window geometry, the default AI agent,
  each task's selected AI agent, and the task-local AI agent session to resume.

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
The reset-session button forgets only the selected task's selected AI-agent
session in `.agent-workspace-state.json`; it does not delete the underlying
Codex or Claude Code conversation data, and it does not affect another agent
type saved for the same task.
The Actions view remembers the selected console page per task. Returning from
Details or Artifacts restores the previous AI-agent or shell tab; on first
task setup the AI-agent tab is shown by default while a shell tab is still
created for quick manual commands.
Before a new or resumed AI session starts, Agent Workspace runs the task check
once and adds only its error report to the initial agent message. The
pre-commit and pre-push hooks run task_check for repositories inside
`tasks/<task>/` and block when it reports task workflow errors.
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

Built-in action buttons call `python -m agent_tools.tools.agent_workspace.actions`
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
commands, settings, localization, markdown, agent runtime/status, process
runtime, console output, GTK desktop, Tk frontend, VTE terminal, web frontend,
and workspace service. Root modules are reserved for package entrypoints,
installation integration, and launcher code.

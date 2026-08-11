# Agent Workspace

`agent_workspace` is the local desktop dashboard for workspace tasks. It is
named around the workspace rather than Codex because the same task layout can be
used by Codex, Claude Code, plain shell sessions, or another local agent.

Launch from the workspace root:

```sh
./agent-workspace
```

Main capabilities:

- browse task directories under `tasks/`;
- render `TASK_DESCRIPTION.md` and `TASK_CONTEXT.md`;
- edit task descriptions from the details context menu;
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
resumes the saved session id when one can be matched to that task and falls
back to the latest Codex session otherwise. Claude Code launches with the task
context prompt, but Agent Workspace does not invent Claude conversation ids;
without a real Claude Code conversation id, the UI keeps the action as a new
launch instead of showing a restore action.
The settings dialog can also set default models and reasoning effort for each
agent. Model fields are combo boxes: Codex choices are loaded from the local
Codex model cache with a built-in fallback list, and Claude Code choices use
the CLI aliases `sonnet`, `opus`, and `fable`. Codex launches use `--model` and
`-c model_reasoning_effort="..."`; Claude Code launches use
`--permission-mode auto`, `--model`, and `--effort`. Empty model and effort
values leave the agent CLI defaults in control. Initial defaults are Codex
`gpt-5.5` with `medium` reasoning and Claude Code `sonnet` with `medium`
effort, so new Agent Workspace installs do not silently launch Claude's
highest-cost default model.
The reset-session button forgets only the selected task's selected AI-agent
session in `.agent-workspace-state.json`; it does not delete the underlying
Codex or Claude Code conversation data, and it does not affect another agent
type saved for the same task.
Task actions are declared by writing `TASK_ACTIONS.json` at the task root. The
GUI watches that file and refreshes its action buttons when it changes.
Task actions launched from the GUI set `PAF_HIDE_TASK_ENV=1`, so PAF does not
dump the full parameter environment into the task console.

Built-in action buttons call `python -m agent_tools.tools.agent_workspace.actions`
instead of keeping the action implementation in the already-running GUI
process. After a GUI version with this runner is started, changes to built-in
action implementation are picked up by the next click without restarting the
window.

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
- run compact `task_check` checks and repository scans through the built-in
  action runner;
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
back to the latest Codex session otherwise. Claude Code uses a task-local
session id and resumes it on the next launch, falling back to its built-in
continue mode only for older task state that has no saved id.
When an agent terminal appears to be waiting for permission or approval, the
task list marks that task with `⚠` to the left of the task name until input is
sent to that agent session or the session closes.

Task actions are declared by writing `TASK_ACTIONS.json` at the task root. The
GUI watches that file and refreshes its action buttons when it changes.
Task actions launched from the GUI set `PAF_HIDE_TASK_ENV=1`, so PAF does not
dump the full parameter environment into the task console.

Built-in action buttons call `python -m agent_tools.tools.agent_workspace.actions`
instead of keeping the action implementation in the already-running GUI
process. After a GUI version with this runner is started, changes to built-in
action implementation are picked up by the next click without restarting the
window.

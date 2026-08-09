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
- manage per-task terminal tabs and one interactive Codex terminal per task;
- open task artifacts from `report/`, `report/diff/`, and `report/puml/`;
- remove artifact files through guarded confirmation dialogs;
- persist theme, language, font sizes, and window geometry.

Task actions are declared by writing `TASK_ACTIONS.json` at the task root. The
GUI watches that file and refreshes its action buttons when it changes.

Built-in action buttons call `python -m agent_tools.tools.agent_workspace.actions`
instead of keeping the action implementation in the already-running GUI
process. After a GUI version with this runner is started, changes to built-in
action implementation are picked up by the next click without restarting the
window.

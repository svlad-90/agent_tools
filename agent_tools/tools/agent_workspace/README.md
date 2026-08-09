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
- run `task_check`, repository scans, and `git status`;
- load task-declared actions from `TASK_ACTIONS.json` and run them in the
  active task terminal;
- manage per-task terminal tabs and one interactive Codex terminal per task;
- open task artifacts from `report/`, `report/diff/`, and `report/puml/`;
- remove artifact files through guarded confirmation dialogs;
- persist theme, language, font sizes, and window geometry.

Task actions are declared by writing `TASK_ACTIONS.json` at the task root. The
GUI watches that file and refreshes its action buttons when it changes.

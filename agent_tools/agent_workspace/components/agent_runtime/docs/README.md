# Agent Runtime Component

Owns agent launch commands, task prompts, runtime environment variables, launch
button state, and agent switch decisions.

Public callers import from `components.agent_runtime.api`.

Runtime command builders keep Codex and Claude Code launch behavior aligned
with the desktop settings:

- default model and reasoning/effort values are passed only when configured;
- Codex receives low-redraw TUI options, including disabled animations by
  default and `tui.disable_mouse_capture=true`;
- Claude Code receives hook settings with `prefersReducedMotion` enabled by
  default, but Agent Workspace does not export `CLAUDE_CODE_DISABLE_MOUSE` so
  Claude's terminal scrollback behavior remains intact;
- both agents receive `AGENT_TOOLS_LIMITED_BASH_OUTPUT_TOKENS`, which controls
  the hook-side Bash output guard.

`ai_agent_environment()` also exports task/session identity variables consumed
by harness hooks, task context injection, status tracking, and task-local log
placement.

# Claude Hooks Component

`claude_hooks` owns the Claude hook subscription API used by Agent Workspace.
The component exposes typed `ClaudeHookEvent` values instead of free-form hook
names. Callers subscribe to one concrete event or to all events with
`subscribe_all`.

The component also owns the command-hook adapter.
`claude_hooks_settings(command)` returns a Claude Code settings fragment for all
supported concrete events. The command can point at:

```sh
python -m agent_tools.agent_workspace.components.claude_hooks.api
```

The command reads Claude hook JSON from stdin, dispatches to subscribers, and
writes JSON hook output to stdout.

The public API lives in `api/__init__.py`. Code outside this component must not
import `src` directly.

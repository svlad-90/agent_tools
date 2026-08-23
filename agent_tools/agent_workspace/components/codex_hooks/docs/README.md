# Codex Hooks Component

`codex_hooks` owns the Codex hook subscription API used by Agent Workspace.
The component exposes typed `CodexHookEvent` values instead of free-form hook
names. Callers subscribe to one concrete event or to all events with
`subscribe_all`.

The component also owns the command-hook adapter. `codex_hooks_config(command)`
returns a Codex hooks mapping for all supported concrete events. The command can
point at:

```sh
python -m agent_tools.agent_workspace.components.codex_hooks.api
```

The command reads Codex hook JSON from stdin, dispatches to subscribers, and
writes JSON hook output to stdout.

The public API lives in `api/__init__.py`. Code outside this component must not
import `src` directly.

# Harness Adapter Component

`harness_adapter` owns Agent Workspace integration with supported agent
harness hooks.

The public API exposes hook configuration helpers, runtime status/debug event
types, debug event storage access, and status subscriptions. Codex-specific
and Claude-specific registries, command parsing, and policy registration are
implementation details under `src/`.

Command entry points:

```sh
python -m agent_tools.agent_workspace.components.harness_adapter.codex
python -m agent_tools.agent_workspace.components.harness_adapter.claude
```

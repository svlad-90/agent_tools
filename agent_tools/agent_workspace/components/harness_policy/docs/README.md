# Harness Policy Component

`harness_policy` contains Agent Workspace behavior built on top of Codex and
Claude hook adapters. It does not parse harness stdin/stdout directly. The hook
components own that boundary.

Public consumers can subscribe to task status updates and read persisted debug
events for a task/session. Workspace composition can register the policy
against Codex or Claude hook registries.

Command entrypoints for real harness configuration are:

```sh
python -m agent_tools.agent_workspace.components.harness_policy.codex
python -m agent_tools.agent_workspace.components.harness_policy.claude
```

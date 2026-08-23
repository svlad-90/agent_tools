# Agent Workspace Settings Component

Owns global Agent Workspace settings, agent defaults, model catalog discovery,
and runtime settings normalization.

Public callers import from `components.settings.api`. Implementation details
such as JSON parsing, CLI model discovery, and value sanitizers stay in `src`.

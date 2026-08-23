# Task Catalog Component

Owns discovery and summary data for task directories under the workspace.

Use only `agent_tools.tools.agent_workspace.components.task_catalog.api` from
outside this component.

The component owns the task-list read model used by service/web frontends:
task directories, `TaskSummary`, task context budget flags, legacy actualize on
GUI discovery, task file reads, and compact task_check reports.

The `src` package is private implementation detail.

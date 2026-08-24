# Agent Workspace Localization Component

Owns localized UI strings and language-specific prompt instructions for Agent
Workspace.

Public callers import from `components.localization.api`. JSON string catalogs
and validation helpers stay in `src`.

Status/tooling labels shown by more than one frontend belong in
`workspace_catalog.json`; GTK-specific labels belong in
`gtk_translation_catalog.json`; Tk-specific labels belong in
`tk_translation_catalog.json`. When adding a visible status icon, update the
tooltip map and manual entries together so the task list, manual popup, and AI
debug surfaces stay consistent.

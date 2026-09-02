---
sync: skill
---

# Python code workflow

These rules apply to all Python code under the workspace root.

1. Use Agent Workspace MCP `code_map_*` tools whenever Python code is
   inspected, changed, reviewed, or validated and those tools are available in
   the active agent client. Use the CLI implementation at
   `agent_tools/tools/code_map` only as fallback.
2. For CLI fallback, run commands from the workspace root or from the
   `agent_tools/` package root. Target file paths are resolved relative to the
   `agent_tools/` package root, not relative to the current shell directory.
   For files under `agent_tools/`, omit the leading `agent_tools/` prefix:

   ```sh
   python -m agent_tools.tools.code_map <command> ...
   python -m agent_tools.tools.code_map map agent_workspace/components/agent_status/src/status.py
   ```

   Do not pass `agent_tools/tools/...` as the target path; from the workspace
   root that resolves to `agent_tools/agent_tools/tools/...`.

3. Before reading or changing an existing Python file, inspect its structure
   with MCP `code_map_map` when available, or with CLI fallback:

   ```sh
   python -m agent_tools.tools.code_map map tools/path/to/file.py
   ```

4. Before changing an existing class, function, or method, resolve its exact
   span and current hash with MCP `code_map_symbol_get` when available, or
   with CLI fallback:

   ```sh
   python -m agent_tools.tools.code_map symbol-get tools/path/to/file.py \
     --symbol QualifiedName
   ```

5. Prefer the guarded symbol and import operations exposed by MCP `code_map_*`
   tools when they fit the change. If another editing mechanism is required,
   still use the map and symbol snapshot to scope the edit.
6. After every Python edit, validate every changed Python file with MCP
   `code_map_parse_check` when available, or with CLI fallback:

   ```sh
   python -m agent_tools.tools.code_map parse-check tools/path/to/file.py
   ```

7. Re-run `map` when a change alters classes, functions, methods, or their
   nesting, and use the relevant audit or diagram command for architectural
   changes.
8. If `code_map` cannot process a file, report the limitation explicitly and
   use the narrowest safe fallback.

Use MCP tool schemas for the compact command reference when available. For CLI
fallback, run `python -m agent_tools.tools.code_map help`.

# Java Code Map JDT Backend

This helper is an internal backend for `agent_tools.tools.java_code_map`.
It is intentionally not exposed as a separate MCP tool. The Python CLI/MCP
layer owns workspace path validation, stable JSON/text output, hash-guarded
edits, and batching; this Java helper owns JDT AST and binding extraction.

Build:

```sh
gradle -p agent_tools/tools/java_code_map/jdt_backend jar
```

Use:

```sh
python -m agent_tools.tools.java_code_map map path/to/Foo.java \
  --ast-backend jdt \
  --jdt-helper agent_tools/tools/java_code_map/jdt_backend/build/libs/java-code-map-jdt-backend.jar \
  --json
```

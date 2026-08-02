# Workspace Tools

This directory owns standalone workspace CLI tools. Run them from the workspace
root through their module entry points:

```sh
python -m codex_tools.tools.code_map
python -m codex_tools.tools.cpp_code_map
python -m codex_tools.tools.yaml_map
python -m codex_tools.tools.diff_report
python -m codex_tools.tools.commit_msg
```

Keep PAF orchestration under `codex_tools/paf_workspace/`; this directory is
for reusable tool implementations that are not PAF domains.

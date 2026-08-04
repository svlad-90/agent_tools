# Workspace Tools

This directory owns standalone workspace CLI tools. Run them from the workspace
root through their module entry points:

```sh
python -m codex_tools.tools.code_map
python -m codex_tools.tools.cpp_code_map
python -m codex_tools.tools.yaml_map
python -m codex_tools.tools.diff_report
python -m codex_tools.tools.commit_msg
python -m codex_tools.tools.push_guard
```

Keep PAF orchestration under `codex_tools/paf_workspace/`; this directory is
for reusable tool implementations that are not PAF domains.

## Push Guard

Use `push_guard` to enforce the workspace rule that every push must follow a
successful build or validation run for the exact commit being pushed:

```sh
python -m codex_tools.tools.push_guard install-hook
python -m codex_tools.tools.push_guard validate -- <build-command>
git push
```

The hook blocks a push when the local commit tip has no recorded successful
validation stamp under the repository's Git metadata.

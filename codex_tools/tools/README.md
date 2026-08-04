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

## Commit Message

Use `commit_msg` to compose and format commit messages from structured parts:

```sh
python -m codex_tools.tools.commit_msg \
  --repo <target-repo> \
  --title "subsys: concise subject" \
  --body "Body paragraphs are wrapped to 72 columns." \
  --signoff "Name <email@example.com>" \
  --reviewed-by "Reviewer <reviewer@example.com>" \
  --tested-by "Tester <tester@example.com>" \
  --acked-by "Acker <acker@example.com>" \
  --assisted-by "Codex:gpt-5 cpp-code-map" \
  --check
```

Use `commit_msg.workflow` when the same structured parts should create or
amend the commit directly:

```sh
python -m codex_tools.tools.commit_msg.workflow \
  --repo <target-repo> \
  --title "subsys: concise subject" \
  --body "Body paragraphs are wrapped to 72 columns." \
  --signoff "Name <email@example.com>" \
  --assisted-by "Codex:gpt-5 cpp-code-map" \
  --commit
```

## Push Guard

Use `push_guard` to enforce the workspace rule that every push must follow a
successful build or validation run for the exact commit being pushed:

```sh
python -m codex_tools.tools.push_guard install-hook
<build-or-validation-command>
python -m codex_tools.tools.push_guard mark-success \
  --source <build-or-validation-id>
git push
```

The hook blocks a push when the local commit tip has no recorded successful
validation stamp under the repository's Git metadata. The same hook also checks
commit messages for pushed commits: every line must fit the configured width
(72 by default), every pushed commit must have a `Signed-off-by` trailer, and
Zephyr repositories must also have a Zephyr-format `Assisted-by` trailer.

For reusable build systems such as PAF, pass the target repository into the PAF
workspace scenario. Its final `push_guard` phase records the same stamp after
the build step has already succeeded:

```sh
python -m codex_tools.tools.push_guard install-hook --repo <target-repo>
codex_tools/paf_workspace/run-paf.sh <scenario-file> <scenario> \
  --parameter PUSH_GUARD_REPO=<target-repo> \
  --parameter PUSH_GUARD_SOURCE=<build-or-validation-id>
git -C <target-repo> push
```

`mark-success` writes the same repository-local validation marker that the
pre-push hook checks. `status` prints whether the current commit already has a
recorded marker:

```sh
python -m codex_tools.tools.push_guard status --repo <target-repo>
```

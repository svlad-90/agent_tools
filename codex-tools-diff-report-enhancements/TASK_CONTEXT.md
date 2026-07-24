# Task Context: Codex Tools Diff Report Enhancements

## Objective

Improve the `codex_tools.diff_report` tooling by splitting the current
monolithic implementation into easier-to-edit parts after first covering the
existing behavior with regression tests.

## Workspace Rules Read

- `codex_tools/rules/python-code.md`
- `codex_tools/rules/cpp-code.md`
- `codex_tools/rules/reusable-environments.md`
- `codex_tools/rules/findings.md`
- `codex_tools/rules/git-commits.md`
- `codex_tools/rules/diff-reports.md`

## Scope

- Target area: `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/diff_report/`
- Expected work: split the diff report implementation into smaller modules
  while preserving current generated-report behavior.
- This task directory owns task-local notes, reproducers, scripts, and report
  artifacts related to those improvements.

## Layout

- `dev/` - development inputs, reproducers, temporary workspaces, or copied test
  fixtures for this task.
- `Dockerfile/` - task-specific environment files if a reproducible container is
  needed.
- `scripts/` - repeatable task-local commands if they become useful.
- `report/` - notes, logs, generated artifacts, and validation outputs.
- `report/diff/` - generated diff report artifacts for this task.
- `report/puml/` - PlantUML sources and adjacent rendered SVGs, if diagrams are
  added.

## Decisions

- Task directory name: `codex-tools-diff-report-enhancements`.
- Baseline report fixture copied from
  `/home/vladyslav_goncharuk/Projects/new_dev/zephyr-pr135-review/report/`.
- The copied baseline report is `pr139-to-local-working-tree` and is the
  agreed validation target for this task.
- Existing working-tree changes in `codex_tools/diff_report/core.py` around
  the always-rendered top button/story script and fixed-position diagram code
  popover are treated as part of the behavior to preserve.
- Workspace `.gitignore` now has explicit allowlist entries for
  `.github/workflows/diff-report.yml` and this task directory so the CI
  workflow, shared script, context, and copied fixture artifacts can be tracked.
- Reusable local GitHub Actions validation lives under
  `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/environments/codex-tools-act/`.
- The first implementation split keeps `codex_tools.diff_report.core` as the
  public orchestration and rendering module while moving immutable data models
  to `codex_tools.diff_report.models`.
- The second implementation split moves git/diff source loading, commit message
  extraction from patches, diff file ordering, and diff statistics into
  `codex_tools.diff_report.diff_source`.
- Workspace-local skills were checked; only `commit-message-format` is present
  and it does not apply to task setup.

## Baseline Fixture

Copied original report artifacts:

- `report/diff/pr139-to-local-working-tree.html`
- `report/diff/pr139-to-local-working-tree.json`
- `report/diff/pr139-to-local-working-tree.patch`
- `report/puml/fdt-review-fix-api-flow.puml`
- `report/puml/fdt-review-fix-api-flow.svg`
- `report/runtime/pr139-fdt-final-runtime-xen419.log`

The JSON references the SVG through `../puml/fdt-review-fix-api-flow.svg` and
the runtime log through `../runtime/pr139-fdt-final-runtime-xen419.log`, so the
copied report keeps the same relative layout.

## Tests

- Added
  `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/diff_report/tests/test_pr139_report_regression.py`.
- Added
  `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/diff_report/tests/test_diff_report_behavior.py`.
- Added implementation modules:
  - `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/diff_report/models.py`
  - `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/diff_report/diff_source.py`
- The tests copy the task-owned baseline fixture into a temporary directory and
  regenerate the report there.
- Covered behavior:
  - rendering from `.patch` plus comments JSON;
  - commit message section;
  - summary diagram and log previews;
  - story navigation markup;
  - inline review comment anchors;
  - embedded diagram SVG and runtime log content;
  - diagram modal template with code links;
  - fixed-position diagram code-popover overlay markup and script hooks;
  - reports without `story` still render the shared story script and top
    button without rendering the story section;
  - `--refresh-targets` preserving all ten PR139 inline anchors with
    `attention=0`;
  - repository range rendering includes commit metadata, commit body, diff
    statistics, and generated diff rows;
  - comments JSON artifact variants render summary blocks, file comments,
    inline range comments, inline SVG diagrams, code links, log files, focus
    metadata, diagram notes, log templates, and current story targets;
  - `--refresh-targets` records current `moved`, `ambiguous`, and `not_found`
    JSON statuses and reports `attention=2` for unresolved targets.

## CI Workflow

- Added `.github/workflows/diff-report.yml`.
- Added `scripts/run-ci.sh` as the shared local/GitHub entry point.
- Added reusable Codex tools act environment under
  `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/environments/codex-tools-act/`.
- The act environment image is `codex-tools-act:24.04` and contains Python,
  Git, Docker CLI, and pinned `act` version `0.2.89`.
- The local act runner maps `ubuntu-latest` to
  `ghcr.io/catthehacker/ubuntu:act-latest`.
- Local validation command:

  ```sh
  codex-tools-diff-report-enhancements/scripts/run-ci.sh
  ```

- Local GitHub Actions validation command:

  ```sh
  codex_tools/environments/codex-tools-act/scripts/validate.sh
  ```

- GitHub Actions runs the same script on `push`, `pull_request`, and
  `workflow_dispatch` when diff-report, code-map, workflow, or task fixture
  paths change.

## Validation

- Task scaffold created.
- `python -m codex_tools.code_map map codex_tools/diff_report/core.py`
  succeeded before inspecting the existing Python implementation.
- `python -m codex_tools.code_map map codex_tools/diff_report/__main__.py`
  succeeded before inspecting the CLI wrapper.
- `python -m codex_tools.code_map map codex_tools/diff_report/__init__.py`
  succeeded before inspecting the package entry point.
- `python -m codex_tools.code_map parse-check codex_tools/diff_report/tests/test_pr139_report_regression.py`
  passed.
- `python -m codex_tools.code_map parse-check codex_tools/diff_report/tests/test_diff_report_behavior.py`
  passed.
- `python -m codex_tools.code_map parse-check codex_tools/diff_report/models.py`
  passed.
- `python -m codex_tools.code_map parse-check codex_tools/diff_report/diff_source.py`
  passed.
- `python -m unittest codex_tools.diff_report.tests.test_pr139_report_regression`
  passed.
- `python -m unittest codex_tools.diff_report.tests.test_diff_report_behavior`
  passed.
- `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed.
- `codex_tools/environments/codex-tools-act/scripts/build.sh` passed and built
  `codex-tools-act:24.04`.
- `codex_tools/environments/codex-tools-act/scripts/check.sh` passed with
  Python 3.12.3, Git 2.43.0, Docker 29.1.3, and act 0.2.89.
- `codex_tools/environments/codex-tools-act/scripts/validate.sh` passed through
  local `act`; the `diff-report-tests` GitHub Actions job succeeded and ran
  the shared `run-ci.sh` script inside the workflow.
- After expanding baseline behavior coverage,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with six
  unittest cases.
- After expanding baseline behavior coverage,
  `codex_tools/environments/codex-tools-act/scripts/validate.sh` passed through
  local `act`; the workflow ran the shared script with six unittest cases.
- After extracting `models.py` and `diff_source.py`,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with six
  unittest cases.
- After extracting `models.py` and `diff_source.py`,
  `codex_tools/environments/codex-tools-act/scripts/validate.sh` passed through
  local `act`; the workflow ran the shared script with six unittest cases.

## Remaining Work

- Continue the conservative module split for
  `codex_tools/diff_report/core.py`.
- Next likely split: move comments JSON loading and normalization while keeping
  shared `refresh-targets` helpers explicit.
- Resolve exact symbol spans with `python -m codex_tools.code_map symbol-get`
  before moving or editing existing functions.
- Run `codex-tools-diff-report-enhancements/scripts/run-ci.sh` after each
  meaningful split.
- Run `codex_tools/environments/codex-tools-act/scripts/validate.sh` before
  considering the workflow path complete.
- Update this context as implementation and validation progress.

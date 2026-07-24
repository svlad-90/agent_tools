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
- The third implementation split moves comments JSON loading and normalization,
  including summary blocks, story steps, diagram/log assets, focus terms,
  diagram notes, and inline range validation, into
  `codex_tools.diff_report.comments`.
- The fourth implementation split moves `--refresh-targets` enrichment, target
  status ordering, moved/ambiguous/not-found matching, and attention reporting
  into `codex_tools.diff_report.refresh`.
- The fifth implementation split moves HTML report rendering helpers into
  `codex_tools.diff_report.render` and moves large static document/header,
  theme, story, and diagram JavaScript/CSS asset builders into
  `codex_tools.diff_report.assets`.
- The duplicate diff line parsing used by `render.py`, `refresh.py`, and
  `diff_source.py` now lives in `codex_tools.diff_report.diff_parse`.
- CLI parsing now lives in `codex_tools.diff_report.cli`; package
  `__init__.py` exposes an explicit public API and lazily delegates `main()`
  to the CLI module.
- Workspace-local skills were checked; only `commit-message-format` is present
  and it does not apply to task setup.
- Report layout now uses breakpoint-driven CSS variables for desktop
  adaptability: the fixed left brand/navigation chrome compresses on laptop
  widths, the main report column is centered inside the remaining viewport, and
  the navigation becomes an in-flow block below 1100px.
- Report font sizes use explicit breakpoint values instead of viewport-width
  scaling so text remains stable while resizing.
- The review navigation tree now includes every file from the rendered diff,
  not only files that have review comments. This fixes reports where changed
  files such as `CMakeLists.txt` were visible in the diff but absent from the
  tree.
- The diagram modal no longer exposes the `General view` button. Search
  navigation remains grouped directly next to the diagram/log search input.
- SVG search highlighting now overrides manually assigned diagram text colors
  so search matches remain red even on focused or code-linked labels.
- On narrow layouts the Settings launcher participates in document flow as a
  sticky full-width control instead of overlaying the report content.
- On narrow layouts the Settings launcher is now visible as an in-flow control
  at the top of the report, hidden while scrolling through ordinary content,
  and shown as a compact fixed control on the right once Review Story is pinned
  as the sticky header.
- SVG search current-match styling uses the same red text color as other
  matches and no longer adds a glow/drop-shadow effect.
- Diagram SVG search now also applies the current-match class to child `tspan`
  nodes so the active match remains red when PlantUML or manual diagram styling
  colors the actual `tspan` rather than the parent `text` node.
- Review Story no longer renders Prev/Next buttons; story selection happens
  through the numbered story cards and keyboard navigation remains handled by
  the shared script.
- Review navigation active-file syncing no longer calls `scrollIntoView()` when
  the navigation tree is in normal page flow, preventing narrow layouts from
  snapping back to the tree while scrolling between files.
- Diagram SVG search applies both match and current-match classes to child
  `tspan` nodes so all found words, not only the active match parent, can be
  painted red over PlantUML/manual fills.
- The left report brand is reduced on medium desktop widths so it fits the
  navigation column without dominating the available vertical space.
- Review Story no longer owns the hamburger Settings button, counter, or inline
  top arrow. Settings and top navigation are rendered as external floating
  controls aligned symmetrically to the left and right edges of the main content
  column.
- The floating Settings and top-arrow controls are equal-sized circular buttons
  positioned just outside the main content column when there is room, with a
  small viewport-edge fallback on narrow layouts.
- The outside-content gap for those floating controls was increased so the
  controls no longer feel attached to the sticky Review Story card.
- The report brand mark/text scale was increased so the fixed brand card reads
  as a deliberate logo block rather than a small element inside a large target
  area.
- SVG search highlighting now uses a temporary inline `fill: #cf222e
  !important` overlay with restoration of the previous inline style so matches
  remain visible even when SVG text is colored directly by PlantUML/manual
  styles.
- The current SVG search match uses a brighter red inline fill and bold,
  underlined CSS styling, while other found SVG text stays plain red.
- SVG search now adds red overlay rectangles for every found substring inside a
  matched SVG text node, keeping the whole matched line red and making the
  exact substring stand out without splitting PlantUML text nodes.
- SVG substring highlighting was simplified to a red outline around the exact
  matched substring. The duplicate text overlay was removed because it made
  dense PlantUML labels harder to read.
- Floating Settings and top-arrow controls now render as a vertical stack on
  the right side of the report, outside the main content column.
- Opening a diagram now places keyboard focus into the diagram search field.
- Settings includes a persisted `Text scale` control with minus, reset, and
  plus actions. The scale adjusts the report body, diff/code, story, and code
  popover text through shared CSS variables.
- The light theme uses less pure-white panel/code/diff colors and stronger
  borders so light-on-light areas have more contrast.
- Comment-attached diff target rows use a green-tinted highlight in the light
  theme while the review comment cards remain warm/yellow, reducing the
  yellow-on-yellow ambiguity.
- The Settings dialog keeps its own fixed text size while Text scale changes
  the report content, preventing the scale controls from visually resizing the
  modal while the value is being changed.
- Diagram search input is scheduled through `requestAnimationFrame` to avoid
  rebuilding SVG search overlays synchronously on every key event.
- Text scale keeps an internal JS value and applies the expensive CSS-variable
  update in `requestAnimationFrame`, while the displayed percentage updates
  immediately.
- Floating Settings is now always visible at the bottom of the right-side
  control stack, while the top-arrow appears above it only after scrolling.
- Story/code target flash now applies as a single block-style animation using
  first/last target row boundaries instead of drawing a separate animated edge
  on every target row.
- Comment target rows now render as a consistent highlighted block across
  added, deleted, and context rows, with shared top/bottom block borders.
- Deleted diff rows that sit between covered new-line rows are now included in
  the same comment target block, so mixed add/delete/context ranges keep a
  continuous left edge.
- Story navigation flash now draws one absolute overlay around the union of the
  target rows and the related review comment instead of animating individual
  table cells.
- When a comment immediately follows its target range, the target range no
  longer draws a bottom border between the code block and the comment card, and
  the comment card no longer draws its old connector pseudo-element.
- Jumps to review comments now scroll to the first line of the related target
  range rather than to the comment card itself.
- Active-file navigation auto-scroll is now limited to fixed-position nav
  layouts; when the tree is part of the page flow on narrow screens it only
  updates the active item and does not call `scrollIntoView()`.
- Medium-width report brand content is centered in its card and scaled up to
  use the available brand area.

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
  - `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/diff_report/comments.py`
  - `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/diff_report/refresh.py`
  - `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/diff_report/render.py`
  - `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/diff_report/assets.py`
  - `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/diff_report/diff_parse.py`
  - `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/diff_report/cli.py`
- Added
  `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/diff_report/tests/test_diff_parse.py`.
- Added
  `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/diff_report/tests/test_public_api.py`.
- Added
  `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/diff_report/tests/test_comments.py`.
- Added
  `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/diff_report/tests/test_refresh.py`.
- Added
  `/home/vladyslav_goncharuk/Projects/new_dev/codex_tools/diff_report/tests/test_cli.py`.
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
- `python -m codex_tools.code_map parse-check codex_tools/diff_report/comments.py`
  passed.
- `python -m codex_tools.code_map parse-check codex_tools/diff_report/refresh.py`
  passed.
- `python -m codex_tools.code_map parse-check codex_tools/diff_report/render.py`
  passed.
- `python -m codex_tools.code_map parse-check codex_tools/diff_report/assets.py`
  passed.
- `python -m codex_tools.code_map parse-check codex_tools/diff_report/diff_parse.py`
  passed.
- `python -m codex_tools.code_map parse-check codex_tools/diff_report/cli.py`
  passed.
- `python -m codex_tools.code_map parse-check codex_tools/diff_report/tests/test_diff_parse.py`
  passed.
- `python -m codex_tools.code_map parse-check codex_tools/diff_report/tests/test_public_api.py`
  passed.
- `python -m codex_tools.code_map parse-check codex_tools/diff_report/tests/test_comments.py`
  passed.
- `python -m codex_tools.code_map parse-check codex_tools/diff_report/tests/test_refresh.py`
  passed.
- `python -m codex_tools.code_map parse-check codex_tools/diff_report/tests/test_cli.py`
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
- After adding responsive report layout CSS,
  `python -m unittest codex_tools.diff_report.tests.test_pr139_report_regression`
  passed with four unittest cases.
- After adding responsive report layout CSS,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with 38
  unittest cases.
- The canonical PR139 report was regenerated at
  `/home/vladyslav_goncharuk/Projects/new_dev/codex-tools-diff-report-enhancements/report/diff/pr139-to-local-working-tree.html`.
- Headless Chrome screenshot checks passed at 1366x768 and 1920x1080 after
  fixing a viewport-width calculation that caused page-level horizontal
  overflow.
- After fixing diagram toolbar/search, full-file navigation, and narrow
  Settings placement, `codex-tools-diff-report-enhancements/scripts/run-ci.sh`
  passed with 38 unittest cases.
- The current generator was checked against
  `/home/vladyslav_goncharuk/Projects/new_dev/zephyr-xenstore-client/report/diff/pr103-strict-review.patch`
  and its JSON comments by rendering `/tmp/pr103-strict-review-regenerated.html`;
  the regenerated tree includes both `CMakeLists.txt` and
  `xenstore-cli/CMakeLists.txt`.
- Headless Chrome screenshot check at 760x640 confirmed Settings no longer
  overlays report content on a narrow desktop window.
- After refining narrow Settings visibility and SVG search current-match
  styling, `python -m unittest
  codex_tools.diff_report.tests.test_pr139_report_regression` passed with four
  unittest cases.
- After refining narrow Settings visibility and SVG search current-match
  styling, `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with
  38 unittest cases.
- Headless Chrome screenshot check at 760x640 confirmed the top-of-report
  Settings placement remains in flow and does not overlay the first report
  sections.
- After moving Settings into the Review Story control row and applying SVG
  current-match styling to `tspan` nodes,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with 38
  unittest cases.
- Headless Chrome screenshot check at 760x640 confirmed story reports no
  longer render a Settings control over the top report sections.
- After removing Review Story Prev/Next buttons, changing Settings to a
  hamburger control, constraining active-file nav scrolling, and expanding SVG
  search highlighting, `codex-tools-diff-report-enhancements/scripts/run-ci.sh`
  passed with 38 unittest cases.
- Headless Chrome screenshot check at 1280x720 confirmed the medium-width brand
  card is compact and aligned with the navigation column.
- After repositioning story controls, changing SVG search highlighting to an
  inline overlay, limiting nav auto-scroll to fixed layouts, and centering the
  medium-width brand, `codex-tools-diff-report-enhancements/scripts/run-ci.sh`
  passed with 38 unittest cases.
- After removing Settings, the story counter, and the inline top arrow from
  Review Story, the regenerated target report contains the Settings hamburger
  as a floating left-side control and the top arrow as a matching floating
  right-side control around the main content column.
- After that control placement change,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with 38
  unittest cases.
- After increasing the logo scale, moving floating controls outside the content
  column, and brightening the current SVG search match,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with 38
  unittest cases.
- After widening the floating-control gap and adding SVG substring overlays,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with 38
  unittest cases.
- After stacking controls on the right, adding diagram-search autofocus,
  adding Text scale, and softening the light theme contrast,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with 38
  unittest cases.
- After adding SVG substring text overlays, separating light-theme comment and
  target colors, and freezing Settings dialog text size,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with 38
  unittest cases.
- After changing SVG substring contrast and deferring diagram search/text scale
  rendering work to animation frames,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with 38
  unittest cases.
- After simplifying SVG substring highlighting, swapping the right-side
  controls, keeping Settings visible, and making comment target ranges render
  as one block, `codex-tools-diff-report-enhancements/scripts/run-ci.sh`
  passed with 38 unittest cases.
- After including intermediate deleted rows in comment target ranges and moving
  story flash to a single external overlay,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with 38
  unittest cases.
- After removing the code/comment separator lines and changing comment jumps to
  land at the beginning of the target block,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with 38
  unittest cases.
- Headless Chrome screenshot check at 1280x720 confirmed the report brand is
  centered and uses more of the available card area.
- After expanding baseline behavior coverage,
  `codex_tools/environments/codex-tools-act/scripts/validate.sh` passed through
  local `act`; the workflow ran the shared script with six unittest cases.
- After extracting `models.py` and `diff_source.py`,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with six
  unittest cases.
- After extracting `models.py` and `diff_source.py`,
  `codex_tools/environments/codex-tools-act/scripts/validate.sh` passed through
  local `act`; the workflow ran the shared script with six unittest cases.
- After extracting `comments.py`,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with six
  unittest cases.
- After extracting `comments.py`,
  `codex_tools/environments/codex-tools-act/scripts/validate.sh` passed through
  local `act`; the workflow ran the shared script with six unittest cases.
- After extracting `refresh.py`,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with six
  unittest cases.
- After extracting `refresh.py`,
  `codex_tools/environments/codex-tools-act/scripts/validate.sh` passed through
  local `act`; the workflow ran the shared script with six unittest cases.
- After extracting `render.py` and `assets.py`,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with six
  unittest cases.
- After extracting `render.py` and `assets.py`,
  `codex_tools/environments/codex-tools-act/scripts/validate.sh` passed through
  local `act`; the workflow ran the shared script with six unittest cases.
- After extracting `diff_parse.py`,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with six
  unittest cases.
- After extracting `diff_parse.py`,
  `codex_tools/environments/codex-tools-act/scripts/validate.sh` passed through
  local `act`; the workflow ran the shared script with six unittest cases.
- After clarifying package imports and adding direct `diff_parse.py` unit tests,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with twelve
  unittest cases.
- Import check confirmed `import codex_tools.diff_report` exposes
  `DiffReportError`, `compact_help`, `generate_report`, and `main` without
  loading `argparse` or `codex_tools.diff_report.cli` until `main()` is called.
- After clarifying package imports and adding direct `diff_parse.py` and public
  API unit tests, `codex_tools/environments/codex-tools-act/scripts/validate.sh`
  passed through local `act`; the workflow ran the shared script with twelve
  unittest cases.
- After adding direct `comments.py` and `refresh.py` unit tests,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with
  twenty-one unittest cases.
- After adding direct `comments.py` and `refresh.py` unit tests,
  `codex_tools/environments/codex-tools-act/scripts/validate.sh` passed through
  local `act`; the workflow ran the shared script with twenty-one unittest
  cases.
- After adding explicit parse-check lines for all diff report test modules,
  `codex_tools/environments/codex-tools-act/scripts/validate.sh` passed through
  local `act`; the workflow ran the shared script with twenty-one unittest
  cases.
- After adding direct CLI tests, `codex-tools-diff-report-enhancements/scripts/run-ci.sh`
  passed with twenty-six unittest cases.
- After adding direct CLI tests,
  `codex_tools/environments/codex-tools-act/scripts/validate.sh` passed through
  local `act`; the workflow ran the shared script with twenty-six unittest
  cases.
- Review pass found that comment text URL linkification could split normal URLs
  after HTML escaping. The renderer now linkifies against raw text segments,
  escapes non-link text separately, and escapes generated href/text values.
- Added behavior coverage for complete URL linkification in summary, file-level,
  and inline review text.
- After fixing the review finding,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with
  twenty-seven unittest cases.
- Added a report UI feature for copying selected diff fragments as Markdown.
  Selecting diff rows or review comments and opening the context menu now shows
  `Copy` and `Copy as Markdown`. `Copy` uses normal browser selection copying;
  `Copy as Markdown` exports the selected report fragment as Markdown.
- The Markdown export groups selected rows by file, preserves the raw rendered
  diff text in fenced `diff` blocks, and includes selected file-level or inline
  review comment text as blockquotes. Partial text selections inside comments
  are copied as partial comment text instead of expanding to the whole comment.
- The old standalone theme toggle was replaced by a global Settings modal with
  Theme options. The theme setting is persisted in `localStorage` and
  synchronizes across open report tabs through browser storage events.
- The Settings modal is centered with an opaque report-styled dialog and
  backdrop instead of a dropdown panel.
- Regenerated
  `report/diff/pr139-to-local-working-tree.html` from the canonical patch and
  comments JSON after adding the selection-copy UI; `--refresh-targets`
  reported `attention=0`.
- After adding Markdown selection copy,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with
  twenty-seven unittest cases.
- Browser automation was not run because Playwright is not installed in the
  workspace Python environment; static HTML checks confirmed the generated
  report contains the selection context menu, diff row metadata, and clipboard
  handler.
- Added comments-filling scaffolding through
  `python -m codex_tools.diff_report --diff-file change.patch --init-comments comments.json`.
  The generated starter JSON keeps renderable comments empty and stores changed
  files plus added-line entries under `_template`, with ready `target` anchors
  for copying into real review comments.
- Verified the scaffolding with the PR139 patch and a generated
  `/tmp/pr139-init-comments.json` template. The full
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` suite passed with
  twenty-nine unittest cases.
- Added a findings-to-comments compose path:
  `python -m codex_tools.diff_report --diff-file change.patch --findings findings.json --output-comments comments.json`.
  Draft findings can target inline comments by explicit `line`, exact
  `content`, or substring `contains`; the composer resolves unique matches and
  writes canonical comments JSON with refreshed `target` anchors.
- Added `dev/pr139-compose-smoke-findings.json` as a task-owned PR139 compose
  input. Regression coverage composes it into temporary comments JSON, renders
  a temporary HTML report, and verifies the generated comments land on
  `arch/arm64/core/reset.S:127` and `arch/arm64/core/xen/fdt.c:56`.
- After adding findings compose support,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with
  thirty-five unittest cases.
- After adding findings compose support,
  `codex_tools/environments/codex-tools-act/scripts/validate.sh` passed through
  local `act`; the workflow ran the shared script with thirty-five unittest
  cases.
- Extended findings compose UX so
  `--findings findings.json --output-comments comments.json --output report.html`
  composes canonical comments and renders HTML in one command when all findings
  resolve cleanly. `--compose-report diagnostics.json` writes unresolved or
  ambiguous finding diagnostics; when diagnostics are present the CLI writes the
  resolved subset to comments JSON but does not render HTML.
- Split large static asset builders out of `assets.py` into focused modules:
  `assets_header.py`, `assets_theme.py`, `assets_story.py`, `assets_copy.py`,
  and `assets_diagram.py`. The original `assets.py` now re-exports the same
  public helper names for compatibility.
- After adding compose UX and splitting static asset modules,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with
  thirty-eight unittest cases.
- After adding compose UX and splitting static asset modules,
  `codex_tools/environments/codex-tools-act/scripts/validate.sh` passed through
  local `act`; the workflow ran the shared script with thirty-eight unittest
  cases.
- Added in-report artifact export controls to the diagram/log modal. Opening a
  diagram shows `Save as SVG`, which downloads the currently opened SVG with
  embedded focus/note styling and animations while removing code-link badges and
  code-link data. Opening a log shows `Save as HTML`, which downloads a
  standalone HTML page containing the full log text.
- Regression coverage now checks the export button markup and JavaScript export
  hooks in the PR139 generated report. After adding artifact export,
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with
  thirty-eight unittest cases.
- After adding artifact export,
  `codex_tools/environments/codex-tools-act/scripts/validate.sh` passed through
  local `act`; the workflow ran the shared script with thirty-eight unittest
  cases.
- Regenerated `report/diff/pr139-to-local-working-tree.html` from the
  canonical patch and comments JSON so the target report includes the artifact
  export controls. `--refresh-targets` reported `attention=0`; static checks
  confirmed `data-asset-export`, `Save as SVG`, `Save as HTML`, and the export
  JavaScript hooks are embedded.
- Updated diagram SVG export to collect relevant CSS rules and current CSS
  variables from the report stylesheet, so exported standalone SVGs preserve
  the same report styling and animations while still removing code-link badges
  and code-link data. Updated story offset calculation to use the sticky story
  panel's actual viewport top plus the maximum story/details height across
  review-history steps, preventing file headers from sliding under or away from
  the story panel when switching between steps with different detail heights.
- Regenerated `report/diff/pr139-to-local-working-tree.html` after the SVG
  export and story-offset fixes. `--refresh-targets` reported `attention=0`;
  static checks confirmed stylesheet-based SVG export and story-offset hooks
  are embedded. `codex-tools-diff-report-enhancements/scripts/run-ci.sh` and
  `codex_tools/environments/codex-tools-act/scripts/validate.sh` both passed
  with thirty-eight unittest cases.
- Reworked standalone SVG export again after visual inspection showed broad
  computed-style inlining damaged PlantUML SVG content in standalone viewers.
  The exporter now preserves the original SVG elements, embeds report CSS
  variables and theme-aware SVG rules, inlines computed styles only for
  report-added overlay nodes such as focus markers and notes, removes code-link
  state, and inserts an explicit export background rectangle so image viewers
  do not show a transparent checkerboard. Regenerated
  `report/diff/pr139-to-local-working-tree.html`; `--refresh-targets` reported
  `attention=0`, static checks confirmed the new export hooks are embedded, and
  both `codex-tools-diff-report-enhancements/scripts/run-ci.sh` and
  `codex_tools/environments/codex-tools-act/scripts/validate.sh` passed with
  thirty-eight unittest cases.
- Tightened standalone SVG export for non-browser Linux SVG viewers. Exported
  CSS rules now resolve report CSS variables to literal colors before download,
  because image viewers do not consistently support browser CSS custom
  properties inside SVG. Note panel opacity is no longer inlined, so browser
  `:hover` rules can reveal diagram info blocks. The left review tree is no
  longer tied to `--story-offset`; that offset is reserved for sticky file
  headers in the main content, so tall review-story details do not push the
  left navigation down. Regenerated
  `report/diff/pr139-to-local-working-tree.html`; `--refresh-targets` reported
  `attention=0`, static checks confirmed the new export hooks and fixed nav
  offset, and both local CI and local `act` workflow validation passed with
  thirty-eight unittest cases.
- Kept browser-oriented SVG export behavior after review: diagram note panels
  remain hover-only, exported SVGs no longer override PlantUML
  `preserveAspectRatio`, and modal initial auto-zoom again uses the previous
  up-to-3x fit behavior. The downloaded SVG copy still removes PlantUML
  `textLength` and `lengthAdjust` text fitting attributes to avoid stretched
  lettering when opened outside the report. Regenerated
  `report/diff/pr139-to-local-working-tree.html`; `--refresh-targets` reported
  `attention=0`, static checks confirmed the restored zoom behavior and absent
  forced `preserveAspectRatio`/visible-note hooks, and both local CI and local
  `act` workflow validation passed with thirty-eight unittest cases.
- Adjusted standalone SVG browser export so the saved file behaves like a large
  fixed-size document when opened directly in a browser. Export CSS no longer
  replays report-container bare `svg` fitting rules such as `max-width: 100%`,
  and the downloaded root SVG gets explicit `width`/`height` and `maxWidth`/
  `maxHeight: none` from its viewBox. The downloaded copy then removes
  `viewBox`, matching manual browser testing where page zoom enlarged the
  diagram uniformly and exposed normal horizontal and vertical scrollbars
  instead of fitting the diagram back into the viewport. Regenerated
  `report/diff/pr139-to-local-working-tree.html`; `--refresh-targets` reported
  `attention=0`, static checks confirmed the export sizing hooks, and both
  local CI and local `act` workflow validation passed with thirty-eight
  unittest cases.
- Adjusted story/file-header positioning to follow the currently visible
  details block. The story script now clears any previously reserved
  `minHeight`, measures the active story panel height, and sets
  `--story-offset` to the current lower edge of the details area. File headers
  can move slightly between story steps, but they stay attached to the visible
  bottom of the active details panel. Regenerated
  `report/diff/pr139-to-local-working-tree.html`; `--refresh-targets` reported
  `attention=0`, static checks confirmed the current-height story offset hook,
  and both local CI and local `act` workflow validation passed with
  thirty-eight unittest cases.
- Comment target blocks now keep diff semantics visible inside the grouped
  block: added rows use a green target tint, deleted rows use a red target
  tint, and unchanged context rows stay neutral with only a light comment-block
  overlay. Regenerated `report/diff/pr139-to-local-working-tree.html`;
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with
  thirty-eight unittest cases.
- Comment rows now continue the diff gutter grid through the empty area beside
  attached review comments: the old/new line-number separators are drawn in
  the comment row background, and the light-theme comment gutter uses the same
  warm family as the comment card instead of reading as target-code green.
  Narrow layouts now keep the Settings and top controls as a right-side
  vertical stack with a fixed gap so they do not overlap when the report is
  collapsed. Regenerated `report/diff/pr139-to-local-working-tree.html`;
  `codex-tools-diff-report-enhancements/scripts/run-ci.sh` passed with
  thirty-eight unittest cases.

## Remaining Work

- Continue conservative splits only where a specific feature needs them.
- `core.py` is now limited to CLI-facing help and report orchestration.
- Remaining split candidates are smaller and optional: split `render.py`
  subareas further if a specific change needs it.
- Resolve exact symbol spans with `python -m codex_tools.code_map symbol-get`
  before moving or editing existing functions.
- Run `codex-tools-diff-report-enhancements/scripts/run-ci.sh` after each
  meaningful split.
- Run `codex_tools/environments/codex-tools-act/scripts/validate.sh` before
  considering the workflow path complete.
- Update this context as implementation and validation progress.

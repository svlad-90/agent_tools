# UI Contract Component

`ui_contract` stores a small normalized tree format for comparing Agent
Workspace frontends. It is a contract-test layer, not a UI generator.

GTK remains the reference for layout and the set of UI controls. Frontend
providers export comparable snapshots with semantic node IDs, roles, child
ordering, normalized widget kinds, layout intent, expansion policy, and numeric
control limits. Tests compare GTK-owned snapshots with Web snapshots so a Web
screen cannot silently drift from the GTK reference while it is ported by hand.

The first contract covers the settings view. It intentionally avoids importing
GTK at test time; the GTK provider is a source-level snapshot of the GTK
settings dialog so it can run in headless CI.

Runtime snapshot support is also available for real widget trees. GTK code
marks significant widgets with semantic node IDs and normalized metadata. The
snapshotter walks the runtime tree, treats unmarked toolkit containers as
transparent, and emits the same `UiTree` shape for comparison against the
source contract or another frontend. The GTK smoke tests include both a small
real-widget tree and the full settings dialog path. The full settings dialog
test patches `Gtk.Dialog.run()` so the dialog is constructed and snapshotted
without entering the modal event loop.

Local validation commands:

```sh
PYTHONPATH=. python -m pytest -q \
  agent_tools/agent_workspace/components/ui_contract/tests/test_ui_contract.py
```

When `pytest` is not installed, use the dependency-free smoke runner:

```sh
PYTHONPATH=. python -m \
  agent_tools.agent_workspace.components.ui_contract.tests.run_smoke
```

The real GTK runtime snapshot test needs a usable GTK display. In headless
environments run it under an external display harness, for example `xvfb-run`,
and add `--require-real-gtk` when a skipped real-GTK snapshot must fail the
validation:

```sh
PYTHONPATH=. xvfb-run -a python -m \
  agent_tools.agent_workspace.components.ui_contract.tests.run_smoke \
  --require-real-gtk
```

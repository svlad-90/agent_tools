from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import SkipTest

from agent_tools.agent_workspace.components.settings.api import AgentModelChoices
from agent_tools.agent_workspace.components.gtk_desktop.src.ui_contract import gtk_settings_ui_tree
from agent_tools.agent_workspace.components.gtk_desktop.src.ui_contract import mark_gtk_widget
from agent_tools.agent_workspace.components.gtk_desktop.src.ui_contract import snapshot_gtk_settings_runtime_tree
from agent_tools.agent_workspace.components.ui_contract.api import UiNode
from agent_tools.agent_workspace.components.ui_contract.api import UiTree
from agent_tools.agent_workspace.components.ui_contract.api import compare_ui_trees
from agent_tools.agent_workspace.components.ui_contract.api import set_ui_contract_metadata
from agent_tools.agent_workspace.components.ui_contract.api import snapshot_widget_tree
from agent_tools.agent_workspace.components.web_frontend.src.ui_contract import web_settings_ui_tree


class FakeWidget:
    def __init__(self, name: str, children: tuple["FakeWidget", ...] = ()) -> None:
        self._name = name
        self._children = children
        self._visible = True
        self._hexpand = False
        self._vexpand = False

    def get_name(self) -> str:
        return self._name

    def get_children(self) -> tuple["FakeWidget", ...]:
        return self._children

    def get_visible(self) -> bool:
        return self._visible

    def get_hexpand(self) -> bool:
        return self._hexpand

    def get_vexpand(self) -> bool:
        return self._vexpand


class FakeDataWidget(FakeWidget):
    def __init__(self, name: str, children: tuple[FakeWidget, ...] = ()) -> None:
        super().__init__(name, children)
        self.data: dict[str, object] = {}

    def __setattr__(self, name: str, value: object) -> None:
        if name == "_agent_tools_ui_contract":
            raise AttributeError(name)
        super().__setattr__(name, value)

    def set_data(self, key: str, value: object) -> None:
        self.data[key] = value

    def get_data(self, key: str) -> object | None:
        return self.data.get(key)


def test_compare_ui_trees_accepts_matching_trees() -> None:
    tree = UiTree(
        frontend="gtk",
        view="settings",
        root_id="settings.dialog",
        nodes=(
            UiNode("settings.dialog", "dialog", children=("settings.tabs",)),
            UiNode("settings.tabs", "tabs", widget="tabs"),
        ),
    )

    assert compare_ui_trees(tree, tree) == []


def test_compare_ui_trees_reports_missing_and_changed_nodes() -> None:
    expected = UiTree(
        frontend="gtk",
        view="settings",
        root_id="settings.dialog",
        nodes=(
            UiNode("settings.dialog", "dialog", children=("settings.tabs",)),
            UiNode("settings.tabs", "tabs", widget="tabs"),
        ),
    )
    actual = UiTree(
        frontend="web",
        view="settings",
        root_id="settings.dialog",
        nodes=(
            UiNode("settings.dialog", "dialog", children=("settings.panel",)),
            UiNode("settings.panel", "section", widget="panel"),
        ),
    )

    issues = compare_ui_trees(expected, actual)

    assert ("settings.tabs", "node") in {(issue.node_id, issue.field) for issue in issues}
    assert ("settings.panel", "node") in {(issue.node_id, issue.field) for issue in issues}
    assert ("settings.dialog", "children") in {(issue.node_id, issue.field) for issue in issues}


def test_snapshot_widget_tree_reads_runtime_widget_metadata() -> None:
    child = FakeWidget("settings.limited_bash_head_tokens")
    container = FakeWidget("GtkBox", (child,))
    root = FakeWidget("settings.bash_output", (container,))
    set_ui_contract_metadata(root, role="section", layout="grid", label_key="settings_section_bash_output")
    set_ui_contract_metadata(
        child,
        role="field",
        widget="number",
        label_key="limited_bash_head_tokens",
        min_value=100,
        max_value=200_000,
        step=100,
    )

    tree = snapshot_widget_tree(root, frontend="gtk", view="settings")
    nodes = tree.node_map()

    assert tree.root_id == "settings.bash_output"
    assert nodes["settings.bash_output"].children == ("settings.limited_bash_head_tokens",)
    assert nodes["settings.bash_output"].layout == "grid"
    assert nodes["settings.limited_bash_head_tokens"].widget == "number"
    assert nodes["settings.limited_bash_head_tokens"].min_value == 100


def test_snapshot_widget_tree_reads_toolkit_data_metadata() -> None:
    field = FakeDataWidget("settings.limited_bash_head_tokens")
    set_ui_contract_metadata(field, role="field", widget="number")

    tree = snapshot_widget_tree(field, frontend="gtk", view="settings")

    assert tree.node_map()["settings.limited_bash_head_tokens"].widget == "number"


def test_snapshot_widget_tree_reads_real_gtk_widgets() -> None:
    try:
        import gi
    except ImportError as exc:
        raise SkipTest(f"PyGObject is unavailable: {exc}") from exc

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    if not Gtk.init_check([])[0]:
        raise SkipTest("GTK display is unavailable")

    dialog = Gtk.Dialog()
    notebook = Gtk.Notebook()
    general = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    bash_output = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    head_tokens = Gtk.SpinButton.new_with_range(100, 200_000, 100)

    mark_gtk_widget(dialog, "settings.dialog", "dialog", layout="window")
    mark_gtk_widget(notebook, "settings.tabs", "tabs", widget_kind="tabs")
    mark_gtk_widget(general, "settings.general", "tab", label_key="settings_dictionary_general", layout="grid")
    mark_gtk_widget(
        bash_output,
        "settings.bash_output",
        "section",
        label_key="settings_section_bash_output",
        layout="grid",
    )
    mark_gtk_widget(
        head_tokens,
        "settings.limited_bash_head_tokens",
        "field",
        label_key="limited_bash_head_tokens",
        widget_kind="number",
        min_value=100,
        max_value=200_000,
        step=100,
    )

    dialog.get_content_area().add(notebook)
    notebook.append_page(general, Gtk.Label(label="General"))
    general.pack_start(bash_output, False, False, 0)
    bash_output.pack_start(head_tokens, False, False, 0)

    try:
        actual = snapshot_widget_tree(dialog, frontend="gtk", view="settings", root_id="settings.dialog")
    finally:
        dialog.destroy()

    expected = UiTree(
        frontend="gtk",
        view="settings",
        root_id="settings.dialog",
        nodes=(
            UiNode("settings.dialog", "dialog", children=("settings.tabs",), layout="window", visible=True),
            UiNode("settings.tabs", "tabs", children=("settings.general",), widget="tabs", visible=True),
            UiNode(
                "settings.general",
                "tab",
                children=("settings.bash_output",),
                label_key="settings_dictionary_general",
                layout="grid",
                visible=True,
            ),
            UiNode(
                "settings.bash_output",
                "section",
                children=("settings.limited_bash_head_tokens",),
                label_key="settings_section_bash_output",
                layout="grid",
                visible=True,
            ),
            UiNode(
                "settings.limited_bash_head_tokens",
                "field",
                label_key="limited_bash_head_tokens",
                widget="number",
                min_value=100,
                max_value=200_000,
                step=100,
                visible=True,
            ),
        ),
    )

    assert [issue.to_json() for issue in compare_ui_trees(expected, actual)] == []


def test_gtk_settings_dialog_runtime_tree_matches_source_contract_ids() -> None:
    try:
        import gi
    except ImportError as exc:
        raise SkipTest(f"PyGObject is unavailable: {exc}") from exc

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    if not Gtk.init_check([])[0]:
        raise SkipTest("GTK display is unavailable")

    from agent_tools.agent_workspace.components.gtk_desktop.src import gtk_ui

    captured: list[UiTree] = []
    original_run = Gtk.Dialog.run
    original_agent_executable = gtk_ui.agent_executable
    original_codex_model_choices_info = gtk_ui.codex_model_choices_info
    original_claude_model_choices_info = gtk_ui.claude_model_choices_info

    def capture_and_cancel(dialog: object) -> object:
        captured.append(snapshot_gtk_settings_runtime_tree(dialog))
        return Gtk.ResponseType.CANCEL

    Gtk.Dialog.run = capture_and_cancel
    gtk_ui.agent_executable = lambda _agent: Path("/tmp/agent-tools-ui-contract-fake-agent")
    gtk_ui.codex_model_choices_info = lambda **_kwargs: AgentModelChoices(("gpt-5",), "test")
    gtk_ui.claude_model_choices_info = lambda: AgentModelChoices(("sonnet",), "test")
    try:
        with TemporaryDirectory() as tmpdir:
            gui = gtk_ui.WorkspaceGtkGui(Path(tmpdir))
            try:
                gui.open_settings()
            finally:
                workspace_ipc_server = getattr(gui, "workspace_ipc_server", None)
                if workspace_ipc_server is not None:
                    workspace_ipc_server.close()
                    gui.workspace_ipc_server = None
                gui.window.destroy()
    finally:
        Gtk.Dialog.run = original_run
        gtk_ui.agent_executable = original_agent_executable
        gtk_ui.codex_model_choices_info = original_codex_model_choices_info
        gtk_ui.claude_model_choices_info = original_claude_model_choices_info

    assert len(captured) == 1
    runtime_tree = captured[0]
    source_tree = gtk_settings_ui_tree()
    runtime_nodes = runtime_tree.node_map()
    source_nodes = source_tree.node_map()

    assert set(runtime_nodes) == set(source_nodes)
    assert runtime_nodes["settings.dialog"].children == source_nodes["settings.dialog"].children
    assert runtime_nodes["settings.tabs"].children == source_nodes["settings.tabs"].children
    assert runtime_nodes["settings.general"].children == source_nodes["settings.general"].children
    assert runtime_nodes["settings.bash_output"].children == source_nodes["settings.bash_output"].children
    assert runtime_nodes["settings.limited_bash_head_tokens"].widget == "number"
    assert runtime_nodes["settings.limited_bash_head_tokens"].min_value == 100
    assert runtime_nodes["settings.limited_bash_head_tokens"].max_value == 200_000
    assert runtime_nodes["settings.limited_bash_heartbeat_tokens"].step == 100


def test_web_settings_contract_matches_gtk_settings_contract() -> None:
    issues = compare_ui_trees(gtk_settings_ui_tree(), web_settings_ui_tree())

    assert [issue.to_json() for issue in issues] == []


def test_settings_contract_includes_limited_bash_split_fields() -> None:
    tree = gtk_settings_ui_tree()
    node_ids = set(tree.node_map())

    assert "settings.limited_bash_head_tokens" in node_ids
    assert "settings.limited_bash_tail_tokens" in node_ids
    assert "settings.limited_bash_heartbeat_seconds" in node_ids
    assert "settings.limited_bash_heartbeat_tokens" in node_ids

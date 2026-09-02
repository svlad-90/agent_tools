from __future__ import annotations

from agent_tools.agent_workspace.components.test_support.src.helpers import *


def test_gtk_task_action_shell_command_runs_in_action_cwd(tmp_path: Path) -> None:
    action = TaskAction(
        action_id="unit",
        label="Unit",
        command=("python", "-m", "pytest"),
        cwd=tmp_path / "scripts",
        env={"FLAG": "hello world"},
    )

    command = gtk_task_action_shell_command(action)

    assert command.startswith(f"cd {tmp_path / 'scripts'} && bash -lc ")
    assert "report/logs" in command
    assert "unit-$(date +%Y%m%d-%H%M%S).log" in command
    assert "tee -a" in command
    assert "FLAG=" in command
    assert "hello world" in command
    assert f"{PAF_HIDE_TASK_ENV_VAR}=1" in command
    assert "python -m pytest" in command
    assert "exit ${PIPESTATUS[0]}" in command


def test_gtk_task_action_selection_shows_only_selected_play_button(tmp_path: Path) -> None:
    build = TaskAction(
        action_id="build",
        label="Build",
        command=("scripts/build.sh",),
        cwd=tmp_path,
        env={},
    )
    test = TaskAction(
        action_id="test",
        label="Test",
        command=("scripts/test.sh",),
        cwd=tmp_path,
        env={},
    )
    build_button = FakeGtkButton()
    test_button = FakeGtkButton()
    build_play = FakeGtkButton()
    test_play = FakeGtkButton()
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.selected_task_action = build
    gui.task_action_buttons = {"build": build_button, "test": test_button}
    gui.task_action_play_buttons = {"build": build_play, "test": test_play}

    gui._update_task_action_button_selection()

    assert "task-action-selected" in build_button.style_context.classes
    assert "task-action-selected" not in test_button.style_context.classes
    assert build_play.visible
    assert build_play.sensitive
    assert not test_play.visible
    assert not test_play.sensitive

    gui.selected_task_action = test
    gui._update_task_action_button_selection()

    assert not build_play.visible
    assert not build_play.sensitive
    assert test_play.visible
    assert test_play.sensitive


def test_gtk_task_action_left_press_selects_in_normal_mode(tmp_path: Path) -> None:
    action = TaskAction(
        action_id="build",
        label="Build",
        command=("scripts/build.sh",),
        cwd=tmp_path,
        env={},
    )
    calls: list[str] = []
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.task_action_reorder_mode = False
    gui._on_task_action_clicked = lambda item: calls.append(item.action_id)  # type: ignore[method-assign]

    result = gui._on_task_action_button_press(FakeGtkButton(), FakeGtkButtonEvent(1), action)  # type: ignore[arg-type]

    assert result is False
    assert calls == ["build"]


def test_gtk_task_action_left_press_does_not_select_in_reorder_mode(tmp_path: Path) -> None:
    action = TaskAction(
        action_id="build",
        label="Build",
        command=("scripts/build.sh",),
        cwd=tmp_path,
        env={},
    )
    calls: list[str] = []
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.task_action_reorder_mode = True
    gui._on_task_action_clicked = lambda item: calls.append(item.action_id)  # type: ignore[method-assign]

    result = gui._on_task_action_button_press(FakeGtkButton(), FakeGtkButtonEvent(1), action)  # type: ignore[arg-type]

    assert result is False
    assert calls == []


def test_gtk_task_action_play_left_press_runs_button_handler(tmp_path: Path) -> None:
    action = TaskAction(
        action_id="build",
        label="Build",
        command=("scripts/build.sh",),
        cwd=tmp_path,
        env={},
    )
    calls: list[str] = []
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.task_action_reorder_mode = False
    gui._on_task_action_play_clicked = lambda _button, item: calls.append(item.action_id)  # type: ignore[method-assign]

    result = gui._on_task_action_play_button_press(FakeGtkButton(), FakeGtkButtonEvent(1), action)  # type: ignore[arg-type]

    assert result is True
    assert calls == ["build"]


def test_load_task_actions_and_run_command(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    scripts = task / "scripts"
    scripts.mkdir(parents=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(task)
    (task / "TASK_ACTIONS.json").write_text(
        json.dumps(
            {
                "actions": [
                    {
                        "id": "unit",
                        "label": "Unit tests",
                        "command": [
                            sys.executable,
                            "-c",
                            (
                                "import os; "
                                "print(os.environ['SAMPLE_FLAG']); "
                                f"print(os.environ['{PAF_HIDE_TASK_ENV_VAR}'])"
                            ),
                        ],
                        "cwd": "scripts",
                        "env": {"SAMPLE_FLAG": "ok"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    actions, errors = load_task_actions(discover_tasks_with_context(task, tmp_path))
    action = next(item for item in actions if item.action_id == "unit")
    report = run_task_action(action)

    assert errors == []
    assert action.label == "Unit tests"
    assert action.cwd == scripts.resolve()
    assert "ok" in report
    assert "\n1\n" in report
    assert "exit code: 0" in report


def test_gtk_task_action_code_path_resolves_shell_wrapper(tmp_path: Path) -> None:
    script = tmp_path / "scripts" / "open-board-webcam.sh"
    script.parent.mkdir()
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    action = TaskAction(
        action_id="webcam",
        label="Open board webcam",
        command=("bash", "scripts/open-board-webcam.sh"),
        cwd=tmp_path,
        env={},
    )
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)

    assert gui._task_action_code_path(action) == script.resolve()


def test_task_action_code_path_rejects_invalid_or_escaping_commands(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.sh"
    outside.write_text("#!/bin/sh\n", encoding="utf-8")

    assert task_action_code_path(
        TaskAction(
            action_id="outside",
            label="Outside",
            command=("bash", str(outside)),
            cwd=tmp_path,
            env={},
        )
    ) is None
    assert task_action_code_path(
        TaskAction(
            action_id="invalid",
            label="Invalid",
            command="'unterminated",
            cwd=tmp_path,
            env={},
        )
    ) is None


def test_task_action_state_helpers_resolve_shortcuts_parameters_and_bindings(tmp_path: Path) -> None:
    parameter = TaskActionParameter(
        name="profile",
        label="Profile",
        parameter_type="choice",
        set_name="profiles",
        default="dev",
    )
    global_parameter = TaskActionParameter(
        name="profile",
        label="Profile",
        parameter_type="choice",
        set_name="profiles",
        default="dev",
        global_name="active_profile",
    )
    action = TaskAction(
        action_id="build",
        label="Build",
        command=("scripts/build.sh",),
        cwd=tmp_path,
        env={},
        parameters=(parameter,),
        bindings={"profile": "release"},
    )
    shortcut = TaskAction(
        action_id="build-release",
        label="Build release",
        command=("scripts/build.sh",),
        cwd=tmp_path,
        env={},
        base_action_id="build",
        is_shortcut=True,
    )
    other_shortcut = TaskAction(
        action_id="test-release",
        label="Test release",
        command=("scripts/test.sh",),
        cwd=tmp_path,
        env={},
        base_action_id="test",
        is_shortcut=True,
    )
    config = TaskActionsConfig(
        actions=[action],
        base_actions=[action],
        parameter_sets={
            "profiles": {
                "dev": {"label": "Dev"},
                "release": {"name": "Release"},
            }
        },
        global_parameter_bindings={"active_profile": "release"},
        errors=[],
    )

    assert shortcuts_for_action(action, [shortcut, other_shortcut]) == [shortcut]
    assert parameter_values(parameter, config) == config.parameter_sets["profiles"]
    assert selected_parameter_value(parameter, {}, config.global_parameter_bindings) == "dev"
    assert selected_parameter_value(parameter, {"profile": "release"}, {}) == "release"
    assert selected_parameter_value(global_parameter, {}, config.global_parameter_bindings) == "release"
    assert parameter_button_label(parameter, config, {"profile": "release"}) == "Profile: Release"
    assert parameter_button_label(parameter, config, {"profile": "missing"}) == "Profile: missing"
    assert bindings_for_action_run(action, "build", {"profile": "dev"}) == {"profile": "dev"}
    assert bindings_for_action_run(action, "other", {"profile": "dev"}) == {"profile": "release"}


def test_task_action_parameter_set_helpers_upsert_rename_and_delete() -> None:
    data: dict[str, object] = {
        "parameter_sets": {
            "profiles": {
                "dev": {"name": "Dev"},
                "release": {"name": "Release"},
            }
        }
    }

    assert upsert_parameter_set_value(data, "profiles", "dev", "release", {"name": "Release copy"}) == "release_2"
    assert data["parameter_sets"] == {
        "profiles": {
            "release": {"name": "Release"},
            "release_2": {"name": "Release copy"},
        }
    }
    assert upsert_parameter_set_value(data, "profiles", "release_2", "prod", {"name": "Prod"}) == "prod"
    assert data["parameter_sets"] == {
        "profiles": {
            "release": {"name": "Release"},
            "prod": {"name": "Prod"},
        }
    }
    assert delete_parameter_set_value(data, "profiles", "release")
    assert not delete_parameter_set_value(data, "profiles", "missing")
    assert data["parameter_sets"] == {"profiles": {"prod": {"name": "Prod"}}}


def test_task_action_parameter_set_helpers_reject_malformed_data() -> None:
    malformed_sets: dict[str, object] = {"parameter_sets": []}
    malformed_values: dict[str, object] = {"parameter_sets": {"profiles": []}}

    assert upsert_parameter_set_value(malformed_sets, "profiles", None, "dev", {"name": "Dev"}) is None
    assert upsert_parameter_set_value(malformed_values, "profiles", None, "dev", {"name": "Dev"}) is None
    assert not delete_parameter_set_value(malformed_sets, "profiles", "dev")
    assert not delete_parameter_set_value(malformed_values, "profiles", "dev")


def test_task_action_shortcut_helpers_add_and_delete() -> None:
    data: dict[str, object] = {
        "shortcuts": [
            {"id": "copy-rpi5", "label": "Copy RPI5", "action": "copy", "bindings": {"board": "rpi5"}},
        ]
    }

    assert add_task_shortcut(data, "copy-rpi6", "Copy RPI6", "copy", {"board": "rpi6"})
    assert data["shortcuts"] == [
        {"id": "copy-rpi5", "label": "Copy RPI5", "action": "copy", "bindings": {"board": "rpi5"}},
        {"id": "copy-rpi6", "label": "Copy RPI6", "action": "copy", "bindings": {"board": "rpi6"}},
    ]
    assert delete_task_shortcut(data, "copy-rpi5")
    assert data["shortcuts"] == [
        {"id": "copy-rpi6", "label": "Copy RPI6", "action": "copy", "bindings": {"board": "rpi6"}},
    ]
    assert not delete_task_shortcut(data, "missing")


def test_task_action_shortcut_helpers_reject_malformed_data() -> None:
    data: dict[str, object] = {"shortcuts": {}}

    assert not add_task_shortcut(data, "copy", "Copy", "copy", {})
    assert not delete_task_shortcut(data, "copy")
    assert data == {"shortcuts": {}}


def test_task_action_parameter_dialog_field_names_merge_schema_initial_and_existing_values() -> None:
    data: dict[str, object] = {
        "parameter_types": {
            "board": {
                "fields": {
                    "name": {"type": "string"},
                    "host": {"type": "string"},
                    "user": {"type": "string"},
                }
            }
        }
    }

    assert parameter_dialog_field_names(
        data,
        "board",
        {"password_file"},
        [{"deployment_folder_name": "lab"}, {"host": "10.0.0.2"}],
    ) == ["name", "host", "password_file", "user", "deployment_folder_name"]
    assert parameter_dialog_field_names({}, "custom", set(), []) == ["name"]


def test_load_task_actions_resolves_parameter_sets_and_shortcuts(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    scripts = task / "scripts"
    scripts.mkdir(parents=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(task)
    (task / "TASK_ACTIONS.json").write_text(
        json.dumps(
            {
                "parameter_types": {
                    "board": {
                        "set": "boards",
                        "fields": {
                            "name": {"type": "string"},
                            "host": {"type": "string"},
                        },
                    }
                },
                "parameter_sets": {
                    "boards": {
                        "rpi5": {
                            "name": "RPI5",
                            "host": "10.13.64.242",
                        },
                        "rpi6": {
                            "name": "RPI6",
                            "host": "10.13.64.243",
                        }
                    }
                },
                "global_parameters": {
                    "board": {
                        "label": "Board",
                        "type": "board",
                        "value": "rpi6",
                    }
                },
                "actions": [
                    {
                        "id": "copy",
                        "label": "Copy",
                        "command": ["printf", "ok"],
                        "cwd": ".",
                        "parameters": [
                            {
                                "name": "board",
                                "label": "Board",
                                "type": "board",
                                "default": "rpi5",
                                "global": "board",
                            }
                        ],
                    }
                ],
                "shortcuts": [
                    {
                        "id": "copy-rpi5",
                        "label": "Copy RPI5",
                        "action": "copy",
                        "bindings": {"board": "rpi5"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    config = load_task_actions_config(discover_tasks_with_context(task, tmp_path))
    shortcut = next(action for action in config.actions if action.action_id == "copy-rpi5")

    assert config.errors == []
    assert config.global_parameter_bindings == {"board": "rpi6"}
    assert [action.action_id for action in config.base_actions] == [
        "workspace:validate",
        "workspace:task-check",
        "copy",
    ]
    copy_action = next(action for action in config.base_actions if action.action_id == "copy")
    assert copy_action.parameters[0].global_name == "board"
    assert shortcut.is_shortcut
    assert shortcut.base_action_id == "copy"
    assert shortcut.env["TASK_ACTION_PARAM_BOARD"] == "rpi6"
    assert shortcut.env["TASK_ACTION_PARAM_BOARD_HOST"] == "10.13.64.243"


def test_gtk_action_ui_string_ids_support_language_fallback() -> None:
    assert gtk_ui_module._ui_string("ru", "action.parameters") == "Параметры"
    assert gtk_ui_module._ui_string("ru", "console.ai_agent") == "ИИ агент"
    assert gtk_ui_module._ui_string("ru", "console.shell") == "терминал"
    assert gtk_ui_module._ui_string("missing", "action.parameters") == "Parameters"
    assert gtk_ui_module._ui_string("ru", "action.add_value", set_name="boards") == "Добавить boards"


def test_task_action_menu_state_helpers_select_labels_and_paths(tmp_path: Path) -> None:
    code_path = tmp_path / "scripts" / "build.sh"

    assert task_reorder_label_key(False) == "action.reorder_actions"
    assert task_reorder_label_key(True) == "action.stop_reorder_actions"
    assert task_parameter_menu_state("rpi5", True).selected_value == "rpi5"
    assert task_parameter_menu_state("rpi5", True).reorder_label_key == "action.stop_reorder_actions"

    action_state = task_action_menu_state(tmp_path, code_path, False)
    assert action_state.actions_file == tmp_path / "TASK_ACTIONS.json"
    assert action_state.code_path == code_path
    assert action_state.reorder_label_key == "action.reorder_actions"

    missing_task_state = task_action_menu_state(None, None, True)
    assert missing_task_state.actions_file is None
    assert missing_task_state.code_path is None
    assert missing_task_state.reorder_label_key == "action.stop_reorder_actions"
    assert task_shortcut_menu_state(False).reorder_label_key == "action.reorder_actions"


def test_gtk_json_reorder_helpers_move_actions_parameters_and_shortcuts() -> None:
    data: dict[str, object] = {
        "actions": [
            {"id": "full"},
            {
                "id": "copy",
                "parameters": [
                    {"name": "board"},
                    {"name": "source"},
                    {"name": "target"},
                ],
            },
        ],
        "shortcuts": [
            {"id": "copy-a"},
            {"id": "copy-b"},
        ],
        "global_parameters": {
            "board": {"value": "rpi5"},
            "image": {"value": "full_ufs_gz"},
        },
    }

    actions = data["actions"]
    shortcuts = data["shortcuts"]
    globals_data = data["global_parameters"]
    assert isinstance(actions, list)
    assert isinstance(shortcuts, list)
    assert isinstance(globals_data, dict)

    assert gtk_ui_module._move_json_list_entry(actions, "id", "copy", -1)
    assert [entry["id"] for entry in actions if isinstance(entry, dict)] == ["copy", "full"]
    assert gtk_ui_module._move_json_list_entry_before(actions, "id", "full", "copy")
    assert [entry["id"] for entry in actions if isinstance(entry, dict)] == ["full", "copy"]

    assert gtk_ui_module._move_action_parameter_entry(data, "copy", "target", -1)
    copy_action = next(entry for entry in actions if isinstance(entry, dict) and entry.get("id") == "copy")
    assert isinstance(copy_action, dict)
    parameters = copy_action["parameters"]
    assert isinstance(parameters, list)
    assert [entry["name"] for entry in parameters if isinstance(entry, dict)] == ["board", "target", "source"]

    assert gtk_ui_module._move_json_list_entry(shortcuts, "id", "copy-a", 1)
    assert [entry["id"] for entry in shortcuts if isinstance(entry, dict)] == ["copy-b", "copy-a"]

    assert gtk_ui_module._move_json_mapping_entry(globals_data, "image", -1)
    assert list(globals_data) == ["image", "board"]
    assert gtk_ui_module._reorder_json_mapping_by_ids(globals_data, ["board", "image"])
    assert list(globals_data) == ["board", "image"]
    assert not gtk_ui_module._reorder_json_mapping_by_ids(globals_data, ["board", "image"])

    preview_order = ["full", "copy", "clean"]
    assert gtk_ui_module._move_id_before(preview_order, "clean", "copy")
    assert preview_order == ["full", "clean", "copy"]
    assert gtk_ui_module._move_id_relative(preview_order, "full", "clean", after=True)
    assert preview_order == ["clean", "full", "copy"]
    assert not gtk_ui_module._move_id_relative(preview_order, "clean", "full", after=False)
    assert preview_order == ["clean", "full", "copy"]
    assert not gtk_ui_module._move_id_relative(preview_order, "copy", "full", after=True)
    assert preview_order == ["clean", "full", "copy"]
    assert gtk_ui_module._reorder_json_list_by_ids(actions, "id", ["copy", "full"])
    assert [entry["id"] for entry in actions if isinstance(entry, dict)] == ["copy", "full"]
    assert gtk_ui_module._reorder_action_parameter_entries(data, "copy", ["source", "target", "board"])
    copy_action = next(entry for entry in actions if isinstance(entry, dict) and entry.get("id") == "copy")
    assert isinstance(copy_action, dict)
    reordered_parameters = copy_action["parameters"]
    assert isinstance(reordered_parameters, list)
    assert [entry["name"] for entry in reordered_parameters if isinstance(entry, dict)] == ["source", "target", "board"]
    shortcut_entries: list[object] = [
        {"id": "other-a"},
        {"id": "copy-a"},
        {"id": "copy-b"},
        {"id": "other-b"},
    ]
    assert gtk_ui_module._reorder_json_list_subset_by_ids(shortcut_entries, "id", ["copy-b", "copy-a"])
    assert [entry["id"] for entry in shortcut_entries if isinstance(entry, dict)] == [
        "other-a",
        "copy-b",
        "copy-a",
        "other-b",
    ]


def test_task_action_order_helper_reorders_supported_groups() -> None:
    data: dict[str, object] = {
        "actions": [
            {"id": "full"},
            {
                "id": "copy",
                "parameters": [
                    {"name": "board"},
                    {"name": "source"},
                    {"name": "target"},
                ],
            },
        ],
        "shortcuts": [
            {"id": "other-a"},
            {"id": "copy-a"},
            {"id": "copy-b"},
            {"id": "other-b"},
        ],
        "global_parameters": {
            "board": {"value": "rpi5"},
            "image": {"value": "full_ufs_gz"},
        },
    }

    assert reorder_task_action_data(data, "action", ["copy", "full"])
    actions = data["actions"]
    assert isinstance(actions, list)
    assert [entry["id"] for entry in actions if isinstance(entry, dict)] == ["copy", "full"]

    assert reorder_task_action_data(data, "shortcut", ["copy-b", "copy-a"])
    shortcuts = data["shortcuts"]
    assert isinstance(shortcuts, list)
    assert [entry["id"] for entry in shortcuts if isinstance(entry, dict)] == [
        "other-a",
        "copy-b",
        "copy-a",
        "other-b",
    ]

    assert reorder_task_action_data(data, "parameter", ["target", "source", "board"], selected_action_id="copy")
    copy_action = next(entry for entry in actions if isinstance(entry, dict) and entry.get("id") == "copy")
    assert isinstance(copy_action, dict)
    parameters = copy_action["parameters"]
    assert isinstance(parameters, list)
    assert [entry["name"] for entry in parameters if isinstance(entry, dict)] == ["target", "source", "board"]

    assert reorder_task_action_data(data, "global_parameter", ["image", "board"])
    global_parameters = data["global_parameters"]
    assert isinstance(global_parameters, dict)
    assert list(global_parameters) == ["image", "board"]

    assert not reorder_task_action_data(data, "parameter", ["board", "source", "target"])
    assert not reorder_task_action_data(data, "missing", [])


def test_gtk_task_actions_mutator_handles_save_reload_noop_and_errors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_path = tmp_path / "tasks" / "sample"
    task_path.mkdir(parents=True)
    task = discover_tasks_with_context(task_path, tmp_path)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.selected_task = task
    gui.task_action_errors = []
    reloads: list[str] = []
    saved: list[dict[str, object]] = []

    gui._require_task = lambda show_dialog=True: gui.selected_task  # type: ignore[method-assign]
    gui._load_task_action_buttons = lambda: reloads.append("reload")  # type: ignore[method-assign]
    gui._update_actions_message = lambda: reloads.append("error")  # type: ignore[method-assign]
    monkeypatch.setattr(gtk_ui_module, "load_task_actions_data", lambda _task: ({"actions": []}, []))
    monkeypatch.setattr(gtk_ui_module, "save_task_actions_data", lambda _task, data: saved.append(dict(data)))

    assert gui._mutate_task_actions_data(lambda data: data.setdefault("changed", True) is True)
    assert saved == [{"actions": [], "changed": True}]
    assert reloads == ["reload"]

    reloads.clear()
    assert not gui._mutate_task_actions_data(lambda _data: False)
    assert reloads == []
    assert not gui._mutate_task_actions_data(lambda _data: False, reload_on_no_change=True)
    assert reloads == ["reload"]

    monkeypatch.setattr(gtk_ui_module, "load_task_actions_data", lambda _task: ({}, ["broken"]))
    assert not gui._mutate_task_actions_data(lambda _data: True)
    assert gui.task_action_errors == ["broken"]
    assert reloads == ["reload", "error"]


def test_gtk_task_action_drag_reorder_sequence_moves_one_slot_at_a_time() -> None:
    order = ["full", "copy", "clean", "webcam"]

    assert gtk_ui_module._move_id_relative(order, "full", "copy", after=True)
    assert order == ["copy", "full", "clean", "webcam"]
    assert gtk_ui_module._move_id_relative(order, "full", "clean", after=True)
    assert order == ["copy", "clean", "full", "webcam"]
    assert gtk_ui_module._move_id_relative(order, "full", "webcam", after=True)
    assert order == ["copy", "clean", "webcam", "full"]

    assert gtk_ui_module._move_id_relative(order, "full", "webcam", after=False)
    assert order == ["copy", "clean", "full", "webcam"]
    assert gtk_ui_module._move_id_relative(order, "full", "clean", after=False)
    assert order == ["copy", "full", "clean", "webcam"]


def test_gtk_task_reorder_edges_do_not_oscillate_after_swap() -> None:
    centers = {
        "copy": 100.0,
        "clean": 200.0,
    }
    order = ["full", "copy", "clean"]

    next_order = gtk_ui_module._task_reorder_order_for_drag_edges(
        order,
        "full",
        centers,
        dragged_left=61.0,
        dragged_right=101.0,
        moving_right=True,
    )
    assert next_order == ["copy", "full", "clean"]

    assert (
        gtk_ui_module._task_reorder_order_for_drag_edges(
            next_order,
            "full",
            centers,
            dragged_left=61.0,
            dragged_right=101.0,
            moving_right=True,
        )
        is None
    )
    assert (
        gtk_ui_module._task_reorder_order_for_drag_edges(
            next_order,
            "full",
            centers,
            dragged_left=101.0,
            dragged_right=141.0,
            moving_right=False,
        )
        is None
    )
    assert gtk_ui_module._task_reorder_order_for_drag_edges(
        next_order,
        "full",
        centers,
        dragged_left=99.0,
        dragged_right=139.0,
        moving_right=False,
    ) == ["full", "copy", "clean"]


def test_gtk_task_action_drag_selection_uses_custom_target_payload() -> None:
    selection = FakeGtkDragSelection()

    gtk_set_task_action_drag_selection(selection, "parameter:source")

    assert selection.data == b"parameter:source"
    assert gtk_task_action_drag_selection_id(selection) == "parameter:source"


def test_load_task_actions_rejects_escaping_cwd(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(task)
    (task / "TASK_ACTIONS.json").write_text(
        json.dumps(
            {
                "actions": [
                    {
                        "id": "bad",
                        "label": "Bad",
                        "command": "echo bad",
                        "cwd": "..",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    actions, errors = load_task_actions(discover_tasks_with_context(task, tmp_path))

    assert [action.action_id for action in actions] == [
        "workspace:validate",
        "workspace:task-check",
    ]
    assert "cwd escapes task" in errors[0]


def test_workspace_standard_task_actions_are_injected_without_task_file(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    actions, errors = load_task_actions(summary)

    assert errors == []
    assert [action.action_id for action in actions] == [
        "workspace:validate",
        "workspace:task-check",
    ]
    assert all(action.source == "workspace" for action in actions)
    assert actions[0].command[:4] == (
        "python3",
        "-m",
        "agent_tools.tools.repo_guard",
        "validate",
    )
    assert actions[1].command == (
        "python3",
        "-m",
        "agent_tools.agent_workspace.actions",
        "task-check",
        "--workspace",
        str(tmp_path),
        "--task",
        str(task),
        "--issues-only",
    )
    assert actions[0].cwd == tmp_path

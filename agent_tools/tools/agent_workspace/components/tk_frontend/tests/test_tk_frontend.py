from __future__ import annotations

from agent_tools.tools.agent_workspace.components.test_support.src.helpers import *


def test_task_table_keyboard_activation_is_ignored() -> None:
    tk_gui = object.__new__(AgentWorkspace)
    gtk_gui = object.__new__(WorkspaceGtkGui)
    ctrl = int(Gdk.ModifierType.CONTROL_MASK)

    assert tk_gui._ignore_task_tree_keyboard_activation(object()) == "break"
    assert tk_gui._on_task_tree_key(FakeTkKeyEvent(keysym="Return")) == "break"
    assert tk_gui._on_task_tree_key(FakeTkKeyEvent(keysym="a", char="a")) == "break"
    assert tk_gui._on_task_tree_key(FakeTkKeyEvent(keysym="Down")) is None
    assert gtk_gui._on_task_view_key_press(object(), FakeGtkKeyEvent(Gdk.KEY_Return))
    assert gtk_gui._on_task_view_key_press(object(), FakeGtkKeyEvent(Gdk.KEY_KP_Enter))
    assert gtk_gui._on_task_view_key_press(object(), FakeGtkKeyEvent(Gdk.KEY_space))
    assert gtk_gui._on_task_view_key_press(object(), FakeGtkKeyEvent(Gdk.KEY_a))
    assert not gtk_gui._on_task_view_key_press(object(), FakeGtkKeyEvent(Gdk.KEY_a, state=ctrl))
    assert not gtk_gui._on_task_view_key_press(object(), FakeGtkKeyEvent(Gdk.KEY_Down))


def test_console_tab_title_numbers_shells_only() -> None:
    assert console_tab_title(1, "shell") == "shell 1"
    assert console_tab_title(2, "shell") == "shell 2"
    assert console_tab_title(0, "codex") == "Codex"
    assert console_tab_title(0, "claude") == "Claude Code"


def test_tk_selectable_task_iid_skips_external_active_tasks(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("agent_tools.tools.agent_workspace.components.task_sessions.src.sessions._process_is_agent_workspace_owner", lambda _pid: True)
    locked_path = tmp_path / "tasks" / "locked-task"
    open_path = tmp_path / "tasks" / "open-task"
    locked_path.mkdir(parents=True)
    open_path.mkdir(parents=True)
    (locked_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(locked_path)
    (open_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(open_path)
    tasks = {task.name: task for task in discover_tasks(tmp_path)}
    locked = tasks["locked-task"]
    open_task = tasks["open-task"]
    save_task_active_agent_run(locked, "codex", "external-run", owner_pid=os.getpid())
    gui = object.__new__(AgentWorkspace)
    gui.tasks = [locked, open_task]
    gui.console_sessions = {}

    assert gui._selectable_task_iid("locked-task") == "1"
    assert gui._selectable_task_iid("open-task") == "1"

    save_task_active_agent_run(open_task, "claude", "second-external-run", owner_pid=os.getpid())
    assert gui._selectable_task_iid(None) is None


def test_tk_refresh_tasks_selects_open_task_when_previous_is_locked(tmp_path: Path, monkeypatch) -> None:
    locked_path = tmp_path / "tasks" / "locked-task"
    open_path = tmp_path / "tasks" / "open-task"
    locked_path.mkdir(parents=True)
    open_path.mkdir(parents=True)
    (locked_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(locked_path)
    (open_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(open_path)
    tasks = {task.name: task for task in discover_tasks(tmp_path)}
    locked = tasks["locked-task"]
    open_task = tasks["open-task"]
    tree = FakeTkTaskTree()
    gui = object.__new__(AgentWorkspace)
    gui.workspace = tmp_path
    gui.selected_task = locked
    gui.task_tree = tree
    gui.summary_var = FakeStringVar("")
    gui.tasks = []
    gui._task_label = lambda task: task.name
    gui._task_tags = lambda _task: ()
    gui._task_agent_status = lambda _task: "□"
    gui._task_is_external_active = lambda task: task.path == locked.path
    gui._on_task_selected = lambda _event: None
    monkeypatch.setattr(
        "agent_tools.tools.agent_workspace.components.tk_frontend.src.ui.discover_tasks",
        lambda _workspace: [locked, open_task],
    )

    gui.refresh_tasks()

    assert gui.tasks == [locked, open_task]
    assert tree.rows["0"]["text"] == "locked-task"
    assert tree.rows["1"]["text"] == "open-task"
    assert tree.selection() == ("1",)
    assert tree.focus_iid == "1"
    assert tree.seen_iids == ["1"]
    assert gui.summary_var.get() == "2 tasks, 0 over context budget"


def test_tk_refresh_tasks_clears_selection_when_all_tasks_locked(tmp_path: Path, monkeypatch) -> None:
    first_path = tmp_path / "tasks" / "first-task"
    second_path = tmp_path / "tasks" / "second-task"
    first_path.mkdir(parents=True)
    second_path.mkdir(parents=True)
    (first_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(first_path)
    (second_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(second_path)
    tasks = discover_tasks(tmp_path)
    tree = FakeTkTaskTree()
    tree.selection_set("stale")
    gui = object.__new__(AgentWorkspace)
    gui.workspace = tmp_path
    gui.selected_task = tasks[0]
    gui.task_tree = tree
    gui.summary_var = FakeStringVar("")
    gui.tasks = []
    gui._task_label = lambda task: task.name
    gui._task_tags = lambda _task: ()
    gui._task_agent_status = lambda _task: "×"
    gui._task_is_external_active = lambda _task: True
    gui._clear_selected_task_view = lambda: setattr(gui, "selected_task", None)
    gui._on_task_selected = lambda _event: None
    monkeypatch.setattr(
        "agent_tools.tools.agent_workspace.components.tk_frontend.src.ui.discover_tasks",
        lambda _workspace: tasks,
    )

    gui.refresh_tasks()

    assert tree.selection() == ()
    assert gui.selected_task is None


def test_tk_task_label_shows_session_discovery_pending_marker(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.task_session_discovery = TaskSessionDiscoveryState(pending={summary.path})

    assert gui._task_label(summary) == "⚙ sample-task"

    gui.task_session_discovery.finish(summary.path)

    assert gui._task_label(summary) == "sample-task"


def test_tk_agent_model_and_effort_are_selected_per_agent() -> None:
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.default_codex_model = "gpt-5.5"
    gui.default_codex_reasoning = "medium"
    gui.default_claude_model = "sonnet"
    gui.default_claude_effort = "low"

    assert gui._agent_model("codex") == "gpt-5.5"
    assert gui._agent_reasoning_effort("codex") == "medium"
    assert gui._agent_model("claude") == "sonnet"
    assert gui._agent_reasoning_effort("claude") == "low"


def test_tk_ai_agent_button_label_reflects_resumable_session(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.selected_task = summary
    gui.workspace = tmp_path
    gui.agent_var = FakeStringVar("claude")
    gui.run_ai_agent_button = FakeButton()
    gui.reset_ai_agent_button = FakeButton()
    gui._running_agent_session = lambda selected_task: None  # type: ignore[method-assign]

    gui._update_ai_agent_button_label()
    assert gui.run_ai_agent_button.text == "Запустить ИИ агента"
    assert gui.reset_ai_agent_button.state == "disabled"

    gui.agent_var = FakeStringVar("codex")
    codex_home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(codex_home))
    codex_session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    codex_session_file = codex_home / ".codex" / "sessions" / f"{codex_session_id}.jsonl"
    codex_session_file.parent.mkdir(parents=True)
    codex_session_file.write_text("{}", encoding="utf-8")
    save_task_agent_session(summary, "codex", session_id=codex_session_id)
    gui.workspace = tmp_path
    gui._update_ai_agent_button_label()

    assert gui.run_ai_agent_button.text == "Восстановить сессию ИИ агента"
    assert gui.reset_ai_agent_button.state == "normal"

    gui.agent_var = FakeStringVar("claude")
    gui._update_ai_agent_button_label()

    assert gui.run_ai_agent_button.text == "Запустить ИИ агента"
    assert gui.reset_ai_agent_button.state == "disabled"

    gui.agent_var = FakeStringVar("codex")
    gui._running_agent_session = lambda selected_task: type("Session", (), {"kind": "codex"})()  # type: ignore[method-assign]
    gui._update_ai_agent_button_label()

    assert gui.run_ai_agent_button.text == "ИИ агент запущен"
    assert gui.reset_ai_agent_button.state == "normal"


def test_tk_agent_selection_warns_before_dropping_saved_session(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    session_file = home / ".codex" / "sessions" / f"{session_id}.jsonl"
    session_file.parent.mkdir(parents=True)
    session_file.write_text("{}", encoding="utf-8")
    save_task_agent_session(summary, "codex", session_id=session_id)
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.selected_task = summary
    gui.workspace = tmp_path
    gui.default_agent = "codex"
    gui.agent_var = FakeStringVar("claude")
    gui._updating_agent_selection = False
    gui._running_agent_session = lambda selected_task: None  # type: ignore[method-assign]
    gui._confirm_saved_agent_session_delete = lambda old_agent, new_agent: False  # type: ignore[method-assign]
    gui._update_ai_agent_button_label = lambda: None  # type: ignore[method-assign]
    gui._refresh_task_session_indicators = lambda: None  # type: ignore[method-assign]
    gui._refresh_tree_selection_style = lambda: None  # type: ignore[method-assign]

    gui._on_agent_selected()

    assert gui.agent_var.get() == "codex"
    assert load_task_agent_session(summary, "codex").session_id == session_id

    gui.agent_var = FakeStringVar("claude")
    gui._confirm_saved_agent_session_delete = lambda old_agent, new_agent: True  # type: ignore[method-assign]
    gui._on_agent_selected()

    assert gui.agent_var.get() == "claude"
    assert load_task_agent(summary, "codex") == "claude"
    assert load_task_agent_session(summary, "codex").session_id is None


def test_tk_task_double_click_opens_task_folder(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.selected_task = summary
    calls: list[Path] = []
    gui.open_task = lambda: calls.append(summary.path)  # type: ignore[method-assign]

    gui._on_task_double_clicked(None)

    assert calls == [summary.path]


def test_tk_custom_action_selects_actions_tab_before_running(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    action = TaskAction("sample", "Sample", "printf ok", task, {})
    selected_pages: list[int] = []
    sent: list[tuple[TaskSummary, str]] = []
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.selected_task = summary
    gui.notebook = type("Notebook", (), {"select": lambda self, page: selected_pages.append(page)})()
    gui._send_command_to_task_console = lambda selected_task, command: sent.append((selected_task, command))  # type: ignore[method-assign]

    gui.run_custom_task_action(action)

    assert selected_pages == [0]
    assert sent and sent[0][0] == summary
    assert "printf ok" in sent[0][1]


def test_tk_console_notebook_double_click_adds_shell_console(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.selected_task = summary
    calls: list[TaskSummary] = []
    gui.new_console = lambda selected_task=None: calls.append(selected_task) or 1  # type: ignore[method-assign]

    result = gui._on_console_notebook_double_clicked(None)

    assert result == "break"
    assert calls == [summary]


def test_tk_control_shortcuts_work_on_cyrillic_layout() -> None:
    ctrl = 0x4
    ctrl_shift = 0x4 | 0x1

    assert _tk_control_shortcut(FakeTkKeyEvent(state=ctrl, keysym="Cyrillic_es")) == "interrupt"
    assert _tk_control_shortcut(FakeTkKeyEvent(state=ctrl_shift, keysym="Cyrillic_es")) == "copy"
    assert _tk_control_shortcut(FakeTkKeyEvent(state=ctrl, char="м")) == "v"
    assert _tk_control_shortcut(FakeTkKeyEvent(state=ctrl, keysym="Cyrillic_ve")) == "d"
    assert _tk_control_shortcut(FakeTkKeyEvent(state=ctrl, keysym="x", keycode=54)) == "interrupt"
    assert _tk_control_shortcut(FakeTkKeyEvent(state=ctrl_shift, keysym="x", keycode=54)) == "copy"
    assert _tk_control_shortcut(FakeTkKeyEvent(state=ctrl, keysym="x", keycode=55)) == "v"
    assert _tk_control_shortcut(FakeTkKeyEvent(state=0, keysym="Cyrillic_es")) is None


def test_tk_ctrl_c_writes_interrupt_to_console() -> None:
    writes: list[tuple[int, bytes]] = []
    session = type("Session", (), {"session_id": 7, "fd": object()})()
    gui = object.__new__(AgentWorkspace)
    gui._active_console = lambda: session  # type: ignore[method-assign]
    gui._write_to_console = lambda session_id, data: writes.append((session_id, data))  # type: ignore[method-assign]

    assert gui._on_console_key(FakeTkKeyEvent(state=0x4, keysym="Cyrillic_es")) == "break"
    assert writes == [(7, b"\x03")]


def test_console_paste_text_normalizes_newlines_without_trailing_enter() -> None:
    assert console_paste_text("one\r\ntwo\r\n") == "one two"
    assert console_paste_text("one\rtwo\n\n") == "one two"
    assert console_paste_text("\n  one  \n\n  two\t\n") == "one two"


def test_console_renderer_does_not_backspace_past_input_floor() -> None:
    gui = object.__new__(AgentWorkspace)
    text = FakeConsoleText("task$ ")
    session = ConsoleSession(
        session_id=1,
        title="1 shell",
        task_path=Path("/tmp/task"),
        kind="shell",
        frame=None,  # type: ignore[arg-type]
        text=text,  # type: ignore[arg-type]
        process=None,  # type: ignore[arg-type]
        fd=None,
        chunks=[],
    )

    gui._set_console_input_floor(session)
    gui._insert_console_chunk(session, ConsoleChunk("abc\b \b\b \b\b \b\b \b", ()))

    assert text.text == "task$ "


def test_tk_agent_output_missing_session_wins_over_permission_prompt(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    save_task_agent_session(summary, "claude", session_id="71ca3372-3c10-4501-ad2a-145c5b9305de")
    session = ConsoleSession(
        session_id=1,
        title="Claude",
        task_path=summary.path,
        kind="claude",
        frame=None,  # type: ignore[arg-type]
        text=FakeConsoleText(""),
        process=None,  # type: ignore[arg-type]
        fd=None,
        chunks=[],
    )
    gui = object.__new__(AgentWorkspace)
    gui.console_sessions = {1: session}
    handled: list[int] = []
    gui._handle_agent_restore_failed = lambda failed_session: handled.append(failed_session.session_id)  # type: ignore[method-assign]

    gui._append_console_output(
        1,
        [
            ConsoleChunk(
                "No conversation found with session ID: 71ca3372-3c10-4501-ad2a-145c5b9305de\n"
                "Would you like to run the following command?",
                (),
            )
        ],
    )

    assert handled == [1]


def test_tk_answered_permission_prompt_does_not_keep_ignored_signature(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    read_fd, write_fd = os.pipe()
    prompt = "Would you like to run the following command?"
    session = ConsoleSession(
        session_id=1,
        title="Codex",
        task_path=summary.path,
        kind="codex",
        frame=None,  # type: ignore[arg-type]
        text=FakeConsoleText(""),
        process=FakeProcess(running=True),  # type: ignore[arg-type]
        fd=write_fd,
        chunks=[ConsoleChunk(prompt, ())],
        busy=False,
        permission_pending=True,
        permission_signature=prompt,
    )
    gui = object.__new__(AgentWorkspace)
    gui.console_sessions = {1: session}
    gui._refresh_task_session_indicators = lambda: None  # type: ignore[method-assign]
    gui._schedule_agent_idle_after_output = lambda active_session: None  # type: ignore[method-assign]

    try:
        gui._write_to_console(1, b"y\r")
        gui._append_console_output(1, [ConsoleChunk("\nAccepted\n", ())])
    finally:
        os.close(read_fd)
        os.close(write_fd)

    assert not session.permission_pending
    assert session.ignored_permission_signature is None


def test_tk_agent_busy_clears_after_quiet_output_without_completion_text(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    session = ConsoleSession(
        session_id=1,
        title="Codex",
        task_path=summary.path,
        kind="codex",
        frame=None,  # type: ignore[arg-type]
        text=FakeConsoleText(""),
        process=FakeProcess(running=True),  # type: ignore[arg-type]
        fd=None,
        chunks=[],
        busy=True,
    )
    gui = object.__new__(AgentWorkspace)
    gui.console_sessions = {1: session}
    calls = {"status": 0}
    gui._refresh_task_session_indicators = lambda: calls.__setitem__("status", calls["status"] + 1)  # type: ignore[method-assign]

    session.output_generation = 7
    gui._mark_agent_idle_if_output_quiet(1, 7)

    assert not session.busy
    assert calls == {"status": 1}


def test_tk_agent_output_refreshes_status_when_process_exits(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    session = ConsoleSession(
        session_id=1,
        title="Codex",
        task_path=summary.path,
        kind="codex",
        frame=FakeFrame(),  # type: ignore[arg-type]
        text=FakeConsoleText(""),
        process=FakeProcess(running=False),  # type: ignore[arg-type]
        fd=None,
        chunks=[],
        exited=True,
    )
    gui = object.__new__(AgentWorkspace)
    gui.console_sessions = {1: session}
    calls = {"button": 0, "status": 0}
    gui._update_ai_agent_button_label = lambda: calls.__setitem__("button", calls["button"] + 1)  # type: ignore[method-assign]
    gui._refresh_task_session_indicators = lambda: calls.__setitem__("status", calls["status"] + 1)  # type: ignore[method-assign]

    gui._append_console_output(1, [ConsoleChunk("[process exited with code 0]\n", ())])

    assert calls == {"button": 1, "status": 1}


def test_tk_stop_console_refreshes_full_agent_status(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    frame = FakeFrame()
    process = FakeProcess(running=True)
    session = ConsoleSession(
        session_id=1,
        title="Codex",
        task_path=summary.path,
        kind="codex",
        frame=frame,  # type: ignore[arg-type]
        text=FakeConsoleText(""),
        process=process,  # type: ignore[arg-type]
        fd=None,
        chunks=[],
        busy=True,
        permission_pending=True,
    )
    gui = object.__new__(AgentWorkspace)
    gui.console_sessions = {1: session}
    gui.console_context_text = None
    gui.console_context_selection = ""
    gui.active_console_id = None
    gui.selected_task = None
    calls = {"button": 0, "status": 0}
    gui._forget_console_tab = lambda closed: None  # type: ignore[method-assign]
    gui._update_ai_agent_button_label = lambda: calls.__setitem__("button", calls["button"] + 1)  # type: ignore[method-assign]
    gui._refresh_task_session_indicators = lambda: calls.__setitem__("status", calls["status"] + 1)  # type: ignore[method-assign]

    gui.stop_console(1)

    assert process.terminated
    assert frame.destroyed
    assert session.exited
    assert not session.busy
    assert not session.permission_pending
    assert calls == {"button": 1, "status": 1}


from __future__ import annotations

from agent_tools.tools.agent_workspace.components.test_support.src.helpers import *


def test_reconcile_task_agent_run_session_persists_real_session_mapping(tmp_path: Path) -> None:
    workspace = tmp_path
    task = workspace / "tasks" / "sample-task"
    sessions = workspace / ".codex" / "sessions"
    sessions.mkdir(parents=True)
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    session_file = sessions / f"rollout-2026-08-10T15-25-48-{session_id}.jsonl"
    prompt = ai_agent_task_context_prompt(summary, workspace)
    session_file.write_text(json.dumps({"message": {"content": prompt}}), encoding="utf-8")

    resolved = reconcile_task_agent_run_session(summary, workspace, "codex", "run-1", home=workspace)

    assert resolved == session_id
    assert load_task_agent_run_session_id(summary, "run-1") == session_id
    assert load_task_agent_session(summary, "codex").session_id == session_id


def test_save_task_agent_run_session_id_rejects_invalid_session_id(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    assert not save_task_agent_run_session_id(summary, "run-1", "not-a-session")
    assert load_task_agent_run_session_id(summary, "run-1") is None


def test_task_agent_state_persists_per_task(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    assert load_task_agent(summary, "claude") == "claude"

    save_task_agent(summary, "codex")

    assert load_task_agent(summary, "claude") == "codex"


def test_task_agent_session_state_preserves_agent_selection(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"

    save_task_agent(summary, "claude")
    save_task_agent_session(summary, "codex", session_id=session_id)
    session = load_task_agent_session(summary, "codex")

    assert load_task_agent(summary, "claude") == "codex"
    assert session.resume is True
    assert session.session_id == session_id


def test_find_task_agent_session_id_is_scoped_to_agent_type(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    claude_session_id = "019feba2-e25e-76e1-9468-aa399758268f"

    save_task_agent_session(summary, "claude", session_id=claude_session_id)

    assert find_task_agent_session_id(summary, workspace, "claude") == claude_session_id
    assert find_task_agent_session_id(summary, workspace, "codex") is None


def test_clear_task_agent_session_clears_current_saved_agent_type(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    claude_session_id = "019feba2-e25e-76e1-9468-aa3997582690"

    save_task_agent_session(summary, "claude", session_id=claude_session_id)

    assert clear_task_agent_session(summary, "claude")

    assert load_task_agent_session(summary, "claude").session_id is None


def test_save_task_agent_session_keeps_only_latest_agent_session(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    codex_session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    claude_session_id = "019feba2-e25e-76e1-9468-aa3997582690"

    save_task_agent_session(summary, "codex", session_id=codex_session_id)
    save_task_agent_session(summary, "claude", session_id=claude_session_id)

    assert load_task_agent(summary, "codex") == "claude"
    assert load_task_agent_session(summary, "codex").session_id is None
    assert load_task_agent_session(summary, "claude").session_id == claude_session_id


def test_task_active_agent_run_tracks_external_owner(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    monkeypatch.setattr("agent_tools.tools.agent_workspace.components.task_sessions.src.sessions._process_is_agent_workspace_owner", lambda _pid: True)

    save_task_active_agent_run(summary, "codex", "run-1", owner_pid=os.getpid())

    active = load_task_active_agent_run(summary)
    assert active is not None
    assert active.agent == "codex"
    assert task_has_external_active_agent_run(summary, set())
    assert not task_has_external_active_agent_run(summary, {"run-1"})
    assert not clear_task_active_agent_run(summary, run_id="other")
    assert clear_task_active_agent_run(summary, run_id="run-1", agent="codex")
    assert load_task_active_agent_run(summary) is None


def test_task_active_agent_run_clears_non_workspace_owner(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    save_task_active_agent_run(summary, "codex", "run-1", owner_pid=os.getpid())
    monkeypatch.setattr("agent_tools.tools.agent_workspace.components.task_sessions.src.sessions._process_is_agent_workspace_owner", lambda _pid: False)

    assert load_task_active_agent_run(summary) is None
    assert "active_agent_run" not in load_task_state(summary)


def test_task_active_agent_run_accepts_legacy_live_workspace_owner(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    save_task_state(
        summary,
        {
            "active_agent_run": {
                "agent": "codex",
                "owner_pid": os.getpid(),
                "run_id": "run-1",
            }
        },
    )
    monkeypatch.setattr("agent_tools.tools.agent_workspace.components.task_sessions.src.sessions._process_is_agent_workspace_owner", lambda _pid: True)
    monkeypatch.setattr("agent_tools.tools.agent_workspace.components.task_sessions.src.sessions._current_boot_id", lambda: "current-boot")
    monkeypatch.setattr("agent_tools.tools.agent_workspace.components.task_sessions.src.sessions._process_start_time_ticks", lambda _pid: 100)
    monkeypatch.setattr("agent_tools.tools.agent_workspace.components.task_sessions.src.sessions._process_start_time_epoch", lambda _pid: os.path.getmtime(task_state_path(summary)) - 10)

    active = load_task_active_agent_run(summary)

    assert active is not None
    assert active.run_id == "run-1"
    assert task_has_external_active_agent_run(summary, set())


def test_task_active_agent_run_clears_reused_pid_after_reboot(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    save_task_active_agent_run(summary, "codex", "run-1", owner_pid=os.getpid())
    monkeypatch.setattr("agent_tools.tools.agent_workspace.components.task_sessions.src.sessions._process_is_agent_workspace_owner", lambda _pid: True)
    monkeypatch.setattr("agent_tools.tools.agent_workspace.components.task_sessions.src.sessions._process_start_time_epoch", lambda _pid: os.path.getmtime(task_state_path(summary)) + 10)

    assert load_task_active_agent_run(summary) is None
    assert "active_agent_run" not in load_task_state(summary)


def test_clear_task_agent_session_removes_empty_session_map(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    save_task_agent(summary, "claude")
    save_task_agent_session(summary, "claude", session_id="019feba2-e25e-76e1-9468-aa399758268f")

    assert clear_task_agent_session(summary, "claude")

    data = json.loads((task / ".agent-workspace-state.json").read_text(encoding="utf-8"))
    assert data == {"agent": "claude"}


def test_reset_task_agent_session_preserves_selected_agent(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    save_task_agent_session(summary, "claude", session_id="019feba2-e25e-76e1-9468-aa399758268f")

    assert reset_task_agent_session(summary, "claude")

    assert load_task_agent(summary, "codex") == "claude"
    assert load_task_agent_session(summary, "claude").session_id is None


def test_reset_task_agent_session_clears_active_run_for_selected_agent(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    monkeypatch.setattr("agent_tools.tools.agent_workspace.components.task_sessions.src.sessions._process_is_agent_workspace_owner", lambda _pid: True)
    save_task_active_agent_run(summary, "codex", "run-1", owner_pid=os.getpid())

    assert reset_task_agent_session(summary, "codex")

    assert load_task_agent(summary, "claude") == "codex"
    assert load_task_active_agent_run(summary) is None


def test_reset_task_agent_session_keeps_other_agent_active_run(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    monkeypatch.setattr("agent_tools.tools.agent_workspace.components.task_sessions.src.sessions._process_is_agent_workspace_owner", lambda _pid: True)
    save_task_active_agent_run(summary, "codex", "run-1", owner_pid=os.getpid())

    assert not reset_task_agent_session(summary, "claude")

    active = load_task_active_agent_run(summary)
    assert active is not None
    assert active.agent == "codex"
    assert active.run_id == "run-1"
    assert load_task_agent(summary, "codex") == "claude"


def test_reset_task_agent_session_selects_agent_even_without_saved_session(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    assert not reset_task_agent_session(summary, "claude")

    assert load_task_agent(summary, "codex") == "claude"


def test_task_session_highlight_uses_each_tasks_saved_agent(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.workspace = tmp_path
    gui.default_agent = "codex"
    gui.agent_var = FakeStringVar("codex")

    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    session_file = home / ".codex" / "sessions" / f"{session_id}.jsonl"
    session_file.parent.mkdir(parents=True)
    session_file.write_text("{}", encoding="utf-8")
    save_task_agent(summary, "codex")
    save_task_agent_session(summary, "codex", session_id=session_id)

    assert gui._task_has_resumable_agent_session(summary)


def test_task_session_highlight_uses_any_saved_agent_session(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.workspace = workspace
    gui.default_agent = "codex"
    save_task_agent_session(summary, "claude", session_id="019feba2-e25e-76e1-9468-aa399758268f")

    assert gui._task_has_resumable_agent_session(summary)


def test_find_latest_codex_session_id_matches_task_prompt(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    sessions = home / ".codex" / "sessions" / "2026" / "08" / "10"
    sessions.mkdir(parents=True)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    session_file = sessions / f"rollout-2026-08-10T15-25-48-{session_id}.jsonl"
    session_file.write_text(
        json.dumps(
            {
                "payload": {
                    "content": [
                        {
                            "text": codex_task_context_message(summary, workspace),
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    assert find_latest_codex_session_id(summary, workspace, home=home) == session_id


def test_find_latest_codex_session_id_scans_beyond_large_prefix(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    sessions = home / ".codex" / "sessions" / "2026" / "08" / "10"
    sessions.mkdir(parents=True)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    session_file = sessions / f"rollout-2026-08-10T15-25-48-{session_id}.jsonl"
    prompt = codex_task_context_message(summary, workspace)
    session_file.write_text(
        ("x" * 70_000)
        + "\n"
        + json.dumps({"payload": {"content": [{"text": prompt}]}}),
        encoding="utf-8",
    )

    assert find_latest_codex_session_id(summary, workspace, home=home) == session_id


def test_find_latest_codex_session_id_uses_cached_session_before_scan(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    save_task_agent_session(summary, "codex", session_id=session_id)

    assert find_latest_codex_session_id(summary, workspace, home=home) == session_id


def test_task_session_discovery_state_plans_unresolved_resume_once(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    save_task_agent(summary, "codex")
    save_task_agent_session(summary, "codex")
    discovery = TaskSessionDiscoveryState()

    assert task_needs_session_discovery(summary)
    assert task_agents_needing_session_discovery(summary) == ("codex",)
    assert discovery.plan([summary]) == (summary,)
    assert discovery.is_pending(summary)
    assert discovery.plan([summary]) == ()

    discovery.finish(summary.path)

    assert not discovery.is_pending(summary)
    assert discovery.plan([summary]) == ()


def test_resolve_task_agent_sessions_persists_discovered_codex_session_id(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    sessions = home / ".codex" / "sessions" / "2026" / "08" / "10"
    sessions.mkdir(parents=True)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    session_file = sessions / f"rollout-2026-08-10T15-25-48-{session_id}.jsonl"
    session_file.write_text(
        json.dumps({"payload": {"content": [{"text": codex_task_context_message(summary, workspace)}]}}),
        encoding="utf-8",
    )
    save_task_agent(summary, "codex")
    save_task_agent_session(summary, "codex")

    assert resolve_task_agent_sessions(summary, workspace, home=home) == ("codex",)

    assert load_task_agent_session(summary, "codex").session_id == session_id
    assert not task_needs_session_discovery(summary)
    assert task_agent_session_markers(summary, workspace) == ("Ⅱ",)


def test_find_latest_claude_session_id_matches_task_prompt(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    sessions = home / ".claude" / "projects" / "-tmp-workspace"
    sessions.mkdir(parents=True)
    old_session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    new_session_id = "019feba2-e25e-76e1-9468-aa3997582690"
    prompt = ai_agent_task_context_prompt(summary, workspace)
    old_file = sessions / f"{old_session_id}.jsonl"
    new_file = sessions / f"{new_session_id}.jsonl"
    other_file = sessions / "019feba2-e25e-76e1-9468-aa3997582691.jsonl"
    old_file.write_text(json.dumps({"message": {"content": prompt}, "sessionId": old_session_id}), encoding="utf-8")
    new_file.write_text(json.dumps({"message": {"content": prompt}, "sessionId": new_session_id}), encoding="utf-8")
    other_file.write_text('{"message": {"content": "other task"}}', encoding="utf-8")
    os.utime(old_file, (100, 100))
    os.utime(new_file, (200, 200))
    os.utime(other_file, (300, 300))

    assert find_latest_claude_session_id(summary, workspace, home=home) == new_session_id


def test_find_latest_claude_session_id_uses_cached_session_before_scan(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    save_task_agent_session(summary, "claude", session_id=session_id)

    assert find_latest_claude_session_id(summary, workspace, home=home) == session_id


def test_codex_session_id_validation_trusts_saved_session_id(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    sessions = home / ".codex" / "sessions" / "2026" / "08" / "10"
    sessions.mkdir(parents=True)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"

    save_task_agent_session(summary, "codex", session_id=session_id)
    assert not codex_session_id_exists(session_id, home=home)
    assert task_agent_session_id_is_valid(summary, workspace, "codex", home=home)

    (sessions / f"rollout-2026-08-10T15-25-48-{session_id}.jsonl").write_text("{}", encoding="utf-8")

    assert codex_session_id_exists(session_id, home=home)
    assert task_agent_session_id_is_valid(summary, workspace, "codex", home=home)


def test_task_has_valid_agent_session_checks_any_agent(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)

    assert not task_has_valid_agent_session(summary, workspace)

    save_task_agent_session(summary, "claude", session_id="019feba2-e25e-76e1-9468-aa399758268f")

    assert task_has_valid_agent_session(summary, workspace)
    assert not task_agent_session_id_is_valid(summary, workspace, "codex")


def test_task_selected_agent_has_resumable_state_uses_saved_agent(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"

    save_task_agent(summary, "claude")
    save_task_agent_session(summary, "claude", session_id=session_id)

    assert task_selected_agent_has_resumable_state(summary, workspace, "codex")
    clear_task_agent_session(summary, "claude")
    assert not task_selected_agent_has_resumable_state(summary, workspace, "codex")


def test_task_agent_session_markers_show_latest_resumable_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    codex_session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    codex_session_file = home / ".codex" / "sessions" / f"{codex_session_id}.jsonl"
    codex_session_file.parent.mkdir(parents=True)
    codex_session_file.write_text("{}", encoding="utf-8")
    save_task_agent_session(summary, "codex", session_id=codex_session_id)
    save_task_agent_session(summary, "claude", session_id="019feba2-e25e-76e1-9468-aa3997582690")

    assert task_agent_session_markers(summary, workspace, home=home) == ("Ⅱ",)
    assert not task_agent_has_resumable_state(summary, workspace, "codex", home=home)


def test_task_session_ui_indicators_do_not_scan_codex_history_without_saved_session_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    save_task_agent(summary, "codex")
    save_task_agent_session(summary, "codex")

    def fail_scan(*_args: object, **_kwargs: object) -> str | None:
        raise AssertionError("UI session indicators must not scan Codex history")

    monkeypatch.setattr("agent_tools.tools.agent_workspace.components.task_sessions.src.sessions.find_latest_codex_session_id", fail_scan)

    assert task_agent_session_markers(summary, workspace) == ()
    assert not task_selected_agent_has_resumable_state(summary, workspace, "codex")
    assert task_agent_selection_with_resumable_fallback(summary, workspace, "codex") == "codex"
    assert task_agent_status_text(summary, workspace, permission_pending=False) == "□"


def test_task_agent_selection_with_resumable_fallback_prefers_saved_session_agent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    codex_session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    codex_session_file = home / ".codex" / "sessions" / f"{codex_session_id}.jsonl"
    codex_session_file.parent.mkdir(parents=True)
    codex_session_file.write_text("{}", encoding="utf-8")
    save_task_agent_session(summary, "codex", session_id=codex_session_id)

    assert task_agent_selection_with_resumable_fallback(summary, workspace, "claude", home=home) == "codex"


def test_claude_resume_flag_uses_latest_matching_local_session(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    sessions = home / ".claude" / "projects" / "-tmp-workspace"
    sessions.mkdir(parents=True)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    prompt = ai_agent_task_context_prompt(summary, workspace)
    (sessions / f"{session_id}.jsonl").write_text(
        json.dumps({"message": {"content": prompt}, "sessionId": session_id}),
        encoding="utf-8",
    )

    save_task_agent_session(summary, "claude")

    assert task_agent_has_resumable_state(summary, workspace, "claude", home=home)
    assert not task_agent_session_id_is_valid(summary, workspace, "claude")
    assert find_task_agent_session_id(summary, workspace, "claude", home=home) == session_id


def test_prepare_task_agent_session_persists_discovered_claude_session_id(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    sessions = home / ".claude" / "projects" / "-tmp-workspace"
    sessions.mkdir(parents=True)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    prompt = ai_agent_task_context_prompt(summary, workspace)
    (sessions / f"{session_id}.jsonl").write_text(
        json.dumps({"message": {"content": prompt}, "sessionId": session_id}),
        encoding="utf-8",
    )
    save_task_agent_session(summary, "claude")

    prepared = prepare_task_agent_session(summary, workspace, "claude", home=home)

    assert prepared.agent == "claude"
    assert prepared.resume
    assert prepared.session_id == session_id
    assert load_task_agent_session(summary, "claude").session_id == session_id


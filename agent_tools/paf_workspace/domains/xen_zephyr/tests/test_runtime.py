from agent_tools.paf_workspace.domains.xen_zephyr.lib.runtime import terminal_safe_line


def test_terminal_safe_line_drops_cursor_position_query() -> None:
    line = "[dom0] \x1b7\x1b[r\x1b[999;999H\x1b[6nroot# ready\n"

    assert terminal_safe_line(line) == "[dom0] root# ready\n"


def test_terminal_safe_line_keeps_runtime_markers() -> None:
    line = "[domu1] BLKFRONT PV DISK PASS\n"

    assert terminal_safe_line(line) == line

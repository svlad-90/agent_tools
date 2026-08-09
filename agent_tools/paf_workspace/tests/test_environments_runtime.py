from __future__ import annotations

from paf_workspace.domains.environments.lib.runtime import cpp_code_map_check_command
from paf_workspace.domains.environments.lib.runtime import workspace_tool_baseline_check_command


def test_cpp_code_map_check_command_runs_optional_source_checks() -> None:
    command = cpp_code_map_check_command(
        source="/workspace/project/src/main.cpp",
        compile_db="/workspace/project/build",
        symbol="Device::start",
        report="/workspace/report/cpp-code-map.json",
    )

    assert "python3 -m agent_tools.tools.cpp_code_map help" in command
    assert "python3 -m agent_tools.tools.cpp_light_code_map help" in command
    assert "python3 -m agent_tools.tools.cpp_code_map doctor" in command
    assert "CPP_CODE_MAP_REPORT=/workspace/report/cpp-code-map.json" in command
    assert "compile_db_entry" in command
    assert 'map "$CPP_CODE_MAP_SOURCE"' in command
    assert 'parse-check "$CPP_CODE_MAP_SOURCE"' in command
    assert 'symbol-get "$CPP_CODE_MAP_SOURCE"' in command
    assert "CPP_CODE_MAP_COMPILE_DB=/workspace/project/build" in command


def test_cpp_code_map_check_command_allows_tool_only_smoke() -> None:
    command = cpp_code_map_check_command()

    assert "import clang.cindex" in command
    assert "import agent_tools" in command
    assert "import tree_sitter" in command
    assert "import tree_sitter_cpp" in command
    assert "if [ -n \"$CPP_CODE_MAP_SOURCE\" ]; then" in command
    assert "/tmp/cpp_code_map_smoke.cpp" in command


def test_workspace_tool_baseline_command_follows_capabilities() -> None:
    command = workspace_tool_baseline_check_command(("workspace_tools",))

    assert "import agent_tools" in command
    assert "import tree_sitter" in command
    assert "import tree_sitter_cpp" in command
    assert "cpp_light_code_map help" in command
    assert "clang.cindex" not in command
    assert "cpp_code_map help" not in command


def test_cpp_source_analysis_capability_adds_cpp_code_map_items() -> None:
    command = workspace_tool_baseline_check_command(("workspace_tools", "cpp_source_analysis"))

    assert "import clang.cindex" in command
    assert "cpp_code_map help" in command

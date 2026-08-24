from __future__ import annotations

import sys

from agent_tools.agent_workspace.components.harness_adapter.src.claude_adapter import ClaudeHookCommandResult
from agent_tools.agent_workspace.components.harness_adapter.src.claude_adapter import ClaudeHookRegistry
from agent_tools.agent_workspace.components.harness_adapter.src.claude_adapter import handle_command_hook as handle_claude_command_hook
from agent_tools.agent_workspace.components.harness_adapter.src.codex_adapter import CodexHookCommandResult
from agent_tools.agent_workspace.components.harness_adapter.src.codex_adapter import CodexHookRegistry
from agent_tools.agent_workspace.components.harness_adapter.src.codex_adapter import handle_command_hook as handle_codex_command_hook

from .claude_policy import register_claude_adapter
from .codex_policy import register_codex_adapter


def handle_codex_adapter_hook(stdin_text: str) -> CodexHookCommandResult:
    registry = CodexHookRegistry()
    register_codex_adapter(registry)
    return handle_codex_command_hook(stdin_text, registry=registry)


def handle_claude_adapter_hook(stdin_text: str) -> ClaudeHookCommandResult:
    registry = ClaudeHookRegistry()
    register_claude_adapter(registry)
    return handle_claude_command_hook(stdin_text, registry=registry)


def codex_main() -> int:
    return _emit_result(handle_codex_adapter_hook(sys.stdin.read()))


def claude_main() -> int:
    return _emit_result(handle_claude_adapter_hook(sys.stdin.read()))


def _emit_result(result: CodexHookCommandResult | ClaudeHookCommandResult) -> int:
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.exit_code

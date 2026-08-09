from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import subprocess

from agent_tools.tools.agent_workspace.core import rough_token_count


AGENT_TOOLS_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = AGENT_TOOLS_ROOT.parent
EXCLUDED_PARTS = {".cache", ".git", "__pycache__", "build", "dev"}

TRACKED_MARKDOWN_TOTAL_BUDGET = 40_000
TRACKED_MARKDOWN_FILE_BUDGET = 5_000
SINGLE_TASK_BOOTSTRAP_TOTAL_BUDGET = 25_000
SINGLE_TASK_BOOTSTRAP_FILE_BUDGET = 3_000
TASK_CONTEXT_FILE_BUDGET = 8_000
LEGACY_OVERSIZED_TASK_CONTEXTS = {
    Path("tasks/zephyr-xenstore-client/TASK_CONTEXT.md"),
    Path("tasks/zephyr-hypercalls/TASK_CONTEXT.md"),
    Path("tasks/zephyr-per-vcpu-events/TASK_CONTEXT.md"),
}


def test_tracked_markdown_stays_within_workspace_token_budget() -> None:
    entries = _markdown_entries(_tracked_markdown_files())

    total_tokens = sum(entry.tokens for entry in entries)
    oversized = [entry for entry in entries if entry.tokens > TRACKED_MARKDOWN_FILE_BUDGET]

    assert total_tokens <= TRACKED_MARKDOWN_TOTAL_BUDGET, _budget_message(
        "tracked markdown total",
        total_tokens,
        TRACKED_MARKDOWN_TOTAL_BUDGET,
        entries,
    )
    assert not oversized, _budget_message(
        "tracked markdown per-file",
        oversized[0].tokens if oversized else 0,
        TRACKED_MARKDOWN_FILE_BUDGET,
        oversized,
    )


def test_single_task_bootstrap_markdown_stays_within_token_budget() -> None:
    entries = _markdown_entries(_single_task_bootstrap_markdown_files())

    total_tokens = sum(entry.tokens for entry in entries)
    oversized = [entry for entry in entries if entry.tokens > SINGLE_TASK_BOOTSTRAP_FILE_BUDGET]

    assert total_tokens <= SINGLE_TASK_BOOTSTRAP_TOTAL_BUDGET, _budget_message(
        "single task bootstrap markdown total",
        total_tokens,
        SINGLE_TASK_BOOTSTRAP_TOTAL_BUDGET,
        entries,
    )
    assert not oversized, _budget_message(
        "single task bootstrap markdown per-file",
        oversized[0].tokens if oversized else 0,
        SINGLE_TASK_BOOTSTRAP_FILE_BUDGET,
        oversized,
    )


def test_task_context_markdown_stays_within_file_budget() -> None:
    entries = _markdown_entries(_top_level_task_context_files())
    oversized = [
        entry
        for entry in entries
        if entry.tokens > TASK_CONTEXT_FILE_BUDGET and entry.path not in LEGACY_OVERSIZED_TASK_CONTEXTS
    ]

    assert not oversized, _budget_message(
        "task context markdown per-file",
        oversized[0].tokens if oversized else 0,
        TASK_CONTEXT_FILE_BUDGET,
        oversized,
    )


class MarkdownEntry:
    def __init__(self, path: Path, tokens: int) -> None:
        self.path = path
        self.tokens = tokens


def _tracked_markdown_files() -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=WORKSPACE_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    paths = []
    for line in result.stdout.splitlines():
        path = Path(line)
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        if not (WORKSPACE_ROOT / path).is_file():
            continue
        paths.append(path)
    return tuple(paths)


def _single_task_bootstrap_markdown_files() -> tuple[Path, ...]:
    paths = []
    for path in (Path("AGENTS.md"), Path("CLAUDE.md")):
        if (WORKSPACE_ROOT / path).is_file():
            paths.append(path)

    paths.extend(_relative_markdown_files(AGENT_TOOLS_ROOT / "rules"))
    paths.append(Path("agent_tools/knowledge/README.md"))
    paths.extend(_relative_markdown_files(AGENT_TOOLS_ROOT / "knowledge" / "topics"))
    paths.extend(
        sorted(
            path.relative_to(WORKSPACE_ROOT)
            for path in (AGENT_TOOLS_ROOT / "skills").glob("*/SKILL.md")
        )
    )

    for path in (
        Path("agent_tools/paf_workspace/templates/TASK_DESCRIPTION.md"),
        Path("agent_tools/paf_workspace/templates/TASK_CONTEXT.md"),
    ):
        if (WORKSPACE_ROOT / path).is_file():
            paths.append(path)
    return tuple(dict.fromkeys(paths))


def _top_level_task_context_files() -> tuple[Path, ...]:
    task_root = WORKSPACE_ROOT / "tasks"
    if task_root.is_dir():
        return tuple(sorted(path.relative_to(WORKSPACE_ROOT) for path in task_root.glob("*/TASK_CONTEXT.md")))
    return tuple(sorted(path.relative_to(WORKSPACE_ROOT) for path in WORKSPACE_ROOT.glob("*/TASK_CONTEXT.md")))


def _relative_markdown_files(directory: Path) -> list[Path]:
    return sorted(path.relative_to(WORKSPACE_ROOT) for path in directory.glob("*.md"))


def _markdown_entries(paths: Iterable[Path]) -> list[MarkdownEntry]:
    entries: list[MarkdownEntry] = []
    for path in paths:
        text = (WORKSPACE_ROOT / path).read_text(encoding="utf-8", errors="replace")
        entries.append(MarkdownEntry(Path(path), rough_token_count(text)))
    return sorted(entries, key=lambda entry: entry.tokens, reverse=True)


def _budget_message(label: str, actual: int, budget: int, entries: list[MarkdownEntry]) -> str:
    top = "\n".join(f"  {entry.tokens:6d} {entry.path}" for entry in entries[:10])
    return f"{label} token budget exceeded: actual={actual}, budget={budget}\nTop markdown files:\n{top}"

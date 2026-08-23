from __future__ import annotations

from agent_tools.agent_workspace.components.test_support.src.helpers import *


def test_rough_token_count_uses_words_and_character_fallback() -> None:
    assert rough_token_count("one two three") == 4
    assert rough_token_count("x" * 20) == 5


def test_render_markdown_chunks_formats_common_blocks() -> None:
    chunks = render_markdown_chunks(
        "# Title\n\n"
        "## Section\n"
        "- `item`\n"
        "| Role | Path |\n"
        "| --- | --- |\n"
        "| `HAL` | dev/hal |\n"
        "\n```"
        "\n"
        "code()\n"
        "```\n"
    )

    rendered = [(chunk.text.strip(), chunk.tag) for chunk in chunks if chunk.text.strip()]

    assert rendered == [
        ("Title", "h1"),
        ("Section", "h2"),
        ("- item", "list"),
        (
            "+----------------------------------------------------------------------------------------------+\n"
            "| Row 1                                                                                        |\n"
            "| Role: HAL                                                                                    |\n"
            "| Path: dev/hal                                                                                |\n"
            "+----------------------------------------------------------------------------------------------+",
            "table",
        ),
        ("code()", "code"),
    ]


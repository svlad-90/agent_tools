from __future__ import annotations


def feed_terminal(terminal: object, text: str) -> None:
    data = text.encode()
    attempts = (
        lambda: terminal.feed_child(text),
        lambda: terminal.feed_child(text, len(text)),
        lambda: terminal.feed_child(data),
        lambda: terminal.feed_child(data, len(data)),
    )
    for attempt in attempts:
        try:
            attempt()
            return
        except TypeError:
            continue
    feed_binary = getattr(terminal, "feed_child_binary", None)
    if feed_binary is not None:
        try:
            feed_binary(data)
            return
        except TypeError:
            feed_binary(data, len(data))
            return
    raise TypeError("VTE Terminal.feed_child signature is unsupported")


def terminal_env(env: dict[str, str]) -> list[str]:
    env.setdefault("TERM", "xterm-256color")
    return [f"{key}={value}" for key, value in env.items()]


def terminal_palette(theme: str) -> tuple[str, ...]:
    if theme == "dark":
        return (
            "#111315",
            "#e06c75",
            "#7ec699",
            "#d19a66",
            "#7aa2f7",
            "#c678dd",
            "#56b6c2",
            "#e8eaed",
            "#5c6370",
            "#ef8088",
            "#98d6ac",
            "#e5c07b",
            "#9ab6ff",
            "#d39aea",
            "#7fd4df",
            "#ffffff",
        )
    return (
        "#202124",
        "#b3261e",
        "#137333",
        "#b06000",
        "#1a5fb4",
        "#8e24aa",
        "#007b83",
        "#f2f2f2",
        "#5f6368",
        "#d93025",
        "#188038",
        "#ea8600",
        "#2f6fbb",
        "#a142f4",
        "#129eaf",
        "#ffffff",
    )

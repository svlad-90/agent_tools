from __future__ import annotations

from agent_tools.tools import knowledge

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import bool_arg, string_arg


def knowledge_tools() -> list[McpTool]:
    return [
        McpTool(
            name="knowledge_list_topics",
            title="Knowledge List Topics",
            description="List workspace knowledge topics.",
            input_schema=_scope_input_schema(),
            handler=_knowledge_list_topics,
        ),
        McpTool(
            name="knowledge_get_topic",
            title="Knowledge Get Topic",
            description="Read one workspace knowledge topic.",
            input_schema=_get_topic_input_schema(),
            handler=_knowledge_get_topic,
        ),
        McpTool(
            name="knowledge_search_topics",
            title="Knowledge Search Topics",
            description="Search workspace knowledge topic text.",
            input_schema=_search_topics_input_schema(),
            handler=_knowledge_search_topics,
        ),
        McpTool(
            name="knowledge_set_topic",
            title="Knowledge Set Topic",
            description="Append one finding to a workspace knowledge topic.",
            input_schema=_set_topic_input_schema(),
            handler=_knowledge_set_topic,
        ),
    ]


def _knowledge_list_topics(_context: ToolContext, arguments: JsonObject) -> ToolResult:
    topics = [
        {"scope": scope, "topic": topic, "path": str(path)}
        for scope, topic, path in knowledge._iter_topic_paths(_scope(arguments, allow_all=True))
    ]
    lines = [f"{item['scope']}\t{item['topic']}\t{item['path']}" for item in topics]
    return ToolResult(text="\n".join(lines).rstrip() + "\n", structured_content={"topics": topics})


def _knowledge_get_topic(_context: ToolContext, arguments: JsonObject) -> ToolResult:
    topic = _topic(arguments)
    with_header = bool_arg(arguments, "with_header", False)
    for scope in knowledge._lookup_scopes(_scope(arguments, allow_all=True)):
        path = knowledge._topic_path(topic, scope=scope)
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8").rstrip()
        text = f"# {scope}:{topic}\n\n{content}\n" if with_header else content + "\n"
        return ToolResult(
            text=text,
            structured_content={"scope": scope, "topic": topic, "path": str(path), "content": content},
        )
    raise ValueError(f"knowledge topic not found: {topic}")


def _knowledge_search_topics(_context: ToolContext, arguments: JsonObject) -> ToolResult:
    query = string_arg(arguments, "query")
    folded_query = query.casefold()
    matches: list[JsonObject] = []
    for scope, topic, path in knowledge._iter_topic_paths(_scope(arguments, allow_all=True)):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if folded_query in line.casefold():
                matches.append({"scope": scope, "topic": topic, "line": line_no, "text": line, "path": str(path)})
    if not matches:
        return ToolResult(
            text=f"knowledge: no matches for {query}\n",
            structured_content={"matches": []},
            is_error=True,
        )
    lines = [f"{item['scope']}:{item['topic']}:{item['line']}: {item['text']}" for item in matches]
    return ToolResult(text="\n".join(lines).rstrip() + "\n", structured_content={"matches": matches})


def _knowledge_set_topic(_context: ToolContext, arguments: JsonObject) -> ToolResult:
    scope = _scope(arguments, allow_all=False)
    topic = _topic(arguments)
    finding = string_arg(arguments, "finding").strip()
    if not finding:
        raise ValueError("finding must not be empty")
    path = knowledge._topic_path(topic, scope=scope)
    path.parent.mkdir(parents=True, exist_ok=True)
    prefix = "" if path.exists() and path.read_text(encoding="utf-8").strip() else f"# {topic}\n\n"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(prefix)
        stream.write(f"- {finding}\n")
    payload = {"scope": scope, "topic": topic, "path": str(path), "finding": finding}
    return ToolResult(text=f"knowledge: wrote {scope}:{topic} -> {path}\n", structured_content=payload)


def _scope(arguments: JsonObject, *, allow_all: bool) -> str:
    choices = ("all", "public", "private") if allow_all else ("public", "private")
    scope = string_arg(arguments, "scope", "all" if allow_all else "private")
    if scope not in choices:
        raise ValueError(f"scope must be one of: {', '.join(choices)}")
    return scope


def _topic(arguments: JsonObject) -> str:
    topic = string_arg(arguments, "topic")
    if not knowledge.TOPIC_RE.fullmatch(topic):
        raise ValueError("topic must match [a-z0-9][a-z0-9_-]*")
    return topic


def _scope_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "scope": {"type": "string", "enum": ["all", "public", "private"], "default": "all"},
        },
        "additionalProperties": False,
    }


def _get_topic_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "scope": {"type": "string", "enum": ["all", "public", "private"], "default": "all"},
            "with_header": {"type": "boolean", "default": False},
        },
        "required": ["topic"],
        "additionalProperties": False,
    }


def _search_topics_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "scope": {"type": "string", "enum": ["all", "public", "private"], "default": "all"},
        },
        "required": ["query"],
        "additionalProperties": False,
    }


def _set_topic_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "finding": {"type": "string"},
            "scope": {"type": "string", "enum": ["public", "private"], "default": "private"},
        },
        "required": ["topic", "finding"],
        "additionalProperties": False,
    }

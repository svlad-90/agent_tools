from __future__ import annotations

from typing import Any

from .schema import UiNode
from .schema import UiTree


METADATA_ATTR = "_agent_tools_ui_contract"


def set_ui_contract_metadata(target: object, **metadata: object) -> None:
    data = dict(metadata)
    try:
        setattr(target, METADATA_ATTR, data)
    except (AttributeError, TypeError):
        pass
    set_data = getattr(target, "set_data", None)
    if callable(set_data):
        try:
            set_data(METADATA_ATTR, data)
        except (RuntimeError, TypeError):
            pass


def snapshot_widget_tree(
    root: object,
    *,
    frontend: str,
    view: str,
    root_id: str | None = None,
) -> UiTree:
    nodes: list[UiNode] = []
    seen: set[int] = set()
    _snapshot_widget(root, nodes, seen)
    if root_id is None:
        root_id = _widget_id(root)
    return UiTree(frontend=frontend, view=view, root_id=root_id, nodes=tuple(nodes))


def _snapshot_widget(widget: object, nodes: list[UiNode], seen: set[int]) -> tuple[str, ...]:
    object_id = id(widget)
    if object_id in seen:
        return ()
    seen.add(object_id)

    node_id = _widget_id(widget)
    child_ids: list[str] = []
    for child in _widget_children(widget):
        child_ids.extend(_snapshot_widget(child, nodes, seen))

    if node_id is None:
        return tuple(child_ids)

    metadata = _widget_metadata(widget)
    nodes.append(
        UiNode(
            node_id,
            str(metadata.get("role", _widget_class_name(widget))),
            children=tuple(child_ids),
            label_key=_optional_str(metadata.get("label_key")),
            widget=_optional_str(metadata.get("widget")),
            layout=_optional_str(metadata.get("layout")),
            orientation=_optional_str(metadata.get("orientation")),
            hexpand=_optional_bool(metadata.get("hexpand", _method_value(widget, "get_hexpand"))),
            vexpand=_optional_bool(metadata.get("vexpand", _method_value(widget, "get_vexpand"))),
            min_value=_optional_int(metadata.get("min_value")),
            max_value=_optional_int(metadata.get("max_value")),
            step=_optional_int(metadata.get("step")),
            width=_optional_int(metadata.get("width")),
            height=_optional_int(metadata.get("height")),
            visible=_optional_bool(metadata.get("visible", _method_value(widget, "get_visible"))),
        )
    )
    return (node_id,)


def _widget_id(widget: object) -> str | None:
    metadata = _widget_metadata(widget)
    node_id = metadata.get("node_id")
    if isinstance(node_id, str) and node_id:
        return node_id
    name = _method_value(widget, "get_name")
    if isinstance(name, str) and name.startswith("settings."):
        return name
    return None


def _widget_metadata(widget: object) -> dict[str, object]:
    raw = getattr(widget, METADATA_ATTR, None)
    if raw is None:
        get_data = getattr(widget, "get_data", None)
        if callable(get_data):
            try:
                raw = get_data(METADATA_ATTR)
            except (RuntimeError, TypeError):
                raw = None
    return raw if isinstance(raw, dict) else {}


def _widget_children(widget: object) -> tuple[object, ...]:
    children = _method_value(widget, "get_children")
    if isinstance(children, (list, tuple)):
        return tuple(children)
    child = _method_value(widget, "get_child")
    if child is not None:
        return (child,)
    return ()


def _method_value(widget: object, method_name: str) -> object | None:
    method = getattr(widget, method_name, None)
    if not callable(method):
        return None
    try:
        return method()
    except TypeError:
        return None


def _widget_class_name(widget: object) -> str:
    return type(widget).__name__


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None

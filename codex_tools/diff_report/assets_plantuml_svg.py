from __future__ import annotations

import re

PINNED_PLANTUML_VERSION = "1.2020.02"
PINNED_PLANTUML_RELEASE_DATE = "Sun Mar 01 12:22:07 EET 2020"
PINNED_PLANTUML_HEADLESS_JAVA_OPTION = "-Djava.awt.headless=true"
PINNED_GRAPHVIZ_DOT_VERSION = "2.43.0"

PLANTUML_PREVIEW_THEMES = {
    "light": {
        "bg": "#ffffff",
        "text": "#111827",
        "line": "#475569",
        "arrow": "#334155",
        "box": "#ffffff",
        "note": "#fff8c5",
        "note_border": "#ca5010",
    },
    "dark": {
        "bg": "#1f1f1f",
        "text": "#d4d4d4",
        "line": "#c5c5c5",
        "arrow": "#f0f6fc",
        "box": "#252526",
        "note": "#3a3217",
        "note_border": "#cca700",
    },
}


def plantuml_svg_styles() -> str:
    """Return the CSS contract for PlantUML-generated SVG diagrams.

    The selectors below intentionally target generated SVG internals. They are
    pinned to PlantUML 1.2020.02; update the constants and tests before
    upgrading PlantUML because element shapes, fill colors, or text layout can
    change between PlantUML releases.
    """
    return """
    /* PlantUML SVG contract: PlantUML 1.2020.02, Graphviz dot 2.43.0, JAVA_TOOL_OPTIONS=-Djava.awt.headless=true. */
    .diagram-preview-canvas svg,
    .diagram-zoom-stage svg { background: var(--diagram-svg-bg) !important; }
    .diagram-preview-canvas svg text:not(.diagram-note-text):not(.diagram-note-marker-text):not(.diagram-code-link-badge-text):not(.asset-focus-match):not(.asset-focus-related-hover),
    .diagram-zoom-stage svg text:not(.diagram-note-text):not(.diagram-note-marker-text):not(.diagram-code-link-badge-text):not(.asset-focus-match):not(.asset-focus-related-hover),
    .diagram-preview-canvas svg tspan:not(.diagram-note-text):not(.diagram-note-marker-text):not(.asset-focus-match):not(.asset-focus-related-hover),
    .diagram-zoom-stage svg tspan:not(.diagram-note-text):not(.diagram-note-marker-text):not(.asset-focus-match):not(.asset-focus-related-hover) { fill: var(--diagram-svg-text) !important; stroke: none !important; }
    .diagram-preview-canvas svg line:not(.asset-focus-connector):not(.diagram-code-link-connector):not(.diagram-note-link),
    .diagram-zoom-stage svg line:not(.asset-focus-connector):not(.diagram-code-link-connector):not(.diagram-note-link),
    .diagram-preview-canvas svg path:not(.asset-focus-object):not(.asset-focus-connector):not(.diagram-note-box):not(.diagram-note-link):not(.diagram-code-link-connector),
    .diagram-zoom-stage svg path:not(.asset-focus-object):not(.asset-focus-connector):not(.diagram-note-box):not(.diagram-note-link):not(.diagram-code-link-connector),
    .diagram-preview-canvas svg polyline:not(.asset-focus-connector):not(.diagram-code-link-connector),
    .diagram-zoom-stage svg polyline:not(.asset-focus-connector):not(.diagram-code-link-connector) { stroke: var(--diagram-svg-line) !important; }
    .diagram-preview-canvas svg polygon:not(.asset-focus-connector):not(.asset-focus-object):not(.diagram-code-link-connector):not([fill="#FFFFFF"]):not([fill="#FEFECE"]):not([fill="#EEEEEE"]):not([fill="#2D2D30"]):not([fill="#252526"]):not([fill="#3B3216"]):not([fill="#FBFB77"]),
    .diagram-zoom-stage svg polygon:not(.asset-focus-connector):not(.asset-focus-object):not(.diagram-code-link-connector):not([fill="#FFFFFF"]):not([fill="#FEFECE"]):not([fill="#EEEEEE"]):not([fill="#2D2D30"]):not([fill="#252526"]):not([fill="#3B3216"]):not([fill="#FBFB77"]) { fill: var(--diagram-svg-arrow) !important; stroke: var(--diagram-svg-arrow) !important; stroke-width: 1.4px !important; }
    .diagram-preview-canvas svg polygon[fill="#FFFFFF"]:not(.asset-focus-object),
    .diagram-zoom-stage svg polygon[fill="#FFFFFF"]:not(.asset-focus-object),
    .diagram-preview-canvas svg polygon[fill="#FEFECE"]:not(.asset-focus-object),
    .diagram-zoom-stage svg polygon[fill="#FEFECE"]:not(.asset-focus-object),
    .diagram-preview-canvas svg polygon[fill="#EEEEEE"]:not(.asset-focus-object),
    .diagram-zoom-stage svg polygon[fill="#EEEEEE"]:not(.asset-focus-object),
    .diagram-preview-canvas svg polygon[fill="#2D2D30"]:not(.asset-focus-object),
    .diagram-zoom-stage svg polygon[fill="#2D2D30"]:not(.asset-focus-object),
    .diagram-preview-canvas svg polygon[fill="#252526"]:not(.asset-focus-object),
    .diagram-zoom-stage svg polygon[fill="#252526"]:not(.asset-focus-object),
    .diagram-preview-canvas svg path[fill="#FFFFFF"]:not(.asset-focus-object),
    .diagram-zoom-stage svg path[fill="#FFFFFF"]:not(.asset-focus-object),
    .diagram-preview-canvas svg path[fill="#FEFECE"]:not(.asset-focus-object),
    .diagram-zoom-stage svg path[fill="#FEFECE"]:not(.asset-focus-object),
    .diagram-preview-canvas svg path[fill="#2D2D30"]:not(.asset-focus-object),
    .diagram-zoom-stage svg path[fill="#2D2D30"]:not(.asset-focus-object),
    .diagram-preview-canvas svg rect:not(.diagram-note-box):not(.diagram-code-link-badge-box),
    .diagram-zoom-stage svg rect:not(.diagram-note-box):not(.diagram-code-link-badge-box),
    .diagram-preview-canvas svg ellipse[fill="#FFFFFF"]:not(.asset-focus-object),
    .diagram-zoom-stage svg ellipse[fill="#FFFFFF"]:not(.asset-focus-object),
    .diagram-preview-canvas svg circle:not(.asset-focus-object),
    .diagram-zoom-stage svg circle:not(.asset-focus-object) { fill: var(--diagram-svg-box-bg) !important; stroke: var(--diagram-svg-line) !important; }
    .diagram-preview-canvas svg ellipse[fill="#D4D4D4"]:not(.asset-focus-object),
    .diagram-zoom-stage svg ellipse[fill="#D4D4D4"]:not(.asset-focus-object),
    .diagram-preview-canvas svg polygon[fill="#D4D4D4"]:not(.asset-focus-object),
    .diagram-zoom-stage svg polygon[fill="#D4D4D4"]:not(.asset-focus-object) { fill: var(--diagram-svg-arrow) !important; stroke: var(--diagram-svg-arrow) !important; }
    .diagram-preview-canvas svg path[fill="#FBFB77"],
    .diagram-zoom-stage svg path[fill="#FBFB77"],
    .diagram-preview-canvas svg polygon[fill="#FBFB77"],
    .diagram-zoom-stage svg polygon[fill="#FBFB77"],
    .diagram-preview-canvas svg rect[fill="#FBFB77"],
    .diagram-zoom-stage svg rect[fill="#FBFB77"],
    .diagram-preview-canvas svg path[fill="#3B3216"],
    .diagram-zoom-stage svg path[fill="#3B3216"],
    .diagram-preview-canvas svg polygon[fill="#3B3216"],
    .diagram-zoom-stage svg polygon[fill="#3B3216"],
    .diagram-preview-canvas svg rect[fill="#3B3216"],
    .diagram-zoom-stage svg rect[fill="#3B3216"] { fill: var(--diagram-svg-note-bg) !important; stroke: var(--comment-border) !important; }
    svg .asset-focus-connector { stroke: var(--diagram-focus) !important; stroke-width: 3px !important; opacity: .95; filter: none; }
    svg line.asset-focus-connector, svg path.asset-focus-connector, svg polyline.asset-focus-connector { stroke-dasharray: 8 8; stroke-linecap: round; animation: focus-dash-flow 2.4s linear infinite; }
    svg line.asset-focus-connector-reverse, svg path.asset-focus-connector-reverse, svg polyline.asset-focus-connector-reverse { animation-name: focus-dash-flow-reverse; }
    svg polygon.asset-focus-connector { fill: var(--diagram-focus) !important; opacity: .95; filter: none; animation: none; }
    svg .asset-focus-object { fill: var(--diagram-focus) !important; fill-opacity: .08 !important; stroke: var(--diagram-focus) !important; stroke-width: 4px !important; stroke-dasharray: 8 8; stroke-linecap: round; stroke-linejoin: round; vector-effect: non-scaling-stroke; filter: drop-shadow(0 0 4px var(--diagram-focus-glow)); animation: focus-dash-flow 2.4s linear infinite; pointer-events: none; }
    svg path.asset-focus-object, svg polyline.asset-focus-object, svg line.asset-focus-object { fill: none !important; fill-opacity: 0 !important; pointer-events: none; }
    svg .asset-focus-match { fill: var(--diagram-focus) !important; stroke: none !important; filter: none; animation: none; }
    .diagram-preview-canvas svg text.asset-focus-match,
    .diagram-zoom-stage svg text.asset-focus-match,
    .diagram-preview-canvas svg tspan.asset-focus-match,
    .diagram-zoom-stage svg tspan.asset-focus-match { fill: var(--diagram-focus) !important; stroke: none !important; }
    .diagram-preview-canvas svg text.asset-focus-contained-text,
    .diagram-zoom-stage svg text.asset-focus-contained-text,
    .diagram-preview-canvas svg tspan.asset-focus-contained-text,
    .diagram-zoom-stage svg tspan.asset-focus-contained-text { fill: var(--diagram-svg-text) !important; stroke: none !important; filter: none; }
    svg .diagram-note-panel { opacity: 0; pointer-events: none; transition: opacity .12s ease; }
    svg .diagram-note-hover .diagram-note-panel, svg .diagram-note-hotspot:hover .diagram-note-panel { opacity: 1; pointer-events: auto; }
    svg .diagram-note-box { fill: var(--diagram-note-bg); stroke: var(--diagram-note-link); stroke-width: 1.8px; rx: 6px; ry: 6px; filter: drop-shadow(0 2px 4px rgba(15,23,42,.22)); }
    svg .diagram-note-box.asset-focus-object { fill: var(--diagram-note-bg) !important; fill-opacity: 1 !important; stroke: var(--diagram-focus) !important; stroke-width: 4px !important; stroke-dasharray: 8 8; stroke-linecap: round; stroke-linejoin: round; vector-effect: non-scaling-stroke; filter: none; animation: focus-dash-flow 2.4s linear infinite; }
    svg .diagram-note-text, svg .diagram-note-text tspan { fill: var(--diagram-note-text) !important; font: 12px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; pointer-events: none; }
    svg .diagram-note-link { fill: none; stroke: var(--diagram-focus); stroke-width: 1.4px; opacity: 0; filter: none; animation: none; }
    svg .diagram-note-marker { fill: var(--diagram-note-marker-bg); stroke: var(--diagram-note-link); stroke-width: 1.8px; filter: drop-shadow(0 1px 2px rgba(15,23,42,.2)); }
    svg .diagram-note-marker-text { fill: var(--diagram-note-link); font: 700 13px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; text-anchor: middle; dominant-baseline: central; pointer-events: none; }
    svg .diagram-note-hotspot { cursor: pointer; }
    svg .diagram-note-hover .diagram-note-box, svg .diagram-note-hotspot:hover .diagram-note-box { fill: var(--diagram-note-hover-bg); stroke: var(--diagram-note-link); stroke-width: 2.4px; }
    svg .diagram-note-hover .diagram-note-marker, svg .diagram-note-hotspot:hover .diagram-note-marker { fill: var(--diagram-note-hover-bg); stroke: var(--diagram-note-link); stroke-width: 2.4px; }
    svg .diagram-note-hover .diagram-note-link, svg .diagram-note-hotspot:hover .diagram-note-link { stroke: var(--diagram-focus); stroke-width: 1.4px; opacity: 0; filter: none; animation: none; }
    svg .diagram-note-hover .diagram-note-text, svg .diagram-note-hotspot:hover .diagram-note-text,
    svg .diagram-note-hover .diagram-note-text tspan, svg .diagram-note-hotspot:hover .diagram-note-text tspan { fill: var(--diagram-note-text) !important; }
    svg .diagram-note-hover .diagram-note-box.asset-focus-object,
    svg .diagram-note-hotspot:hover .diagram-note-box.asset-focus-object { fill: var(--diagram-note-bg) !important; fill-opacity: 1 !important; stroke: var(--diagram-focus) !important; stroke-width: 4px !important; stroke-dasharray: 8 8; stroke-linecap: round; stroke-linejoin: round; vector-effect: non-scaling-stroke; filter: none; animation: focus-dash-flow 2.4s linear infinite; }
    svg .diagram-code-link-target { fill: var(--diagram-link) !important; text-decoration: underline; text-decoration-thickness: 1.5px; }
    svg .diagram-code-link-connector { stroke: var(--diagram-link) !important; stroke-width: 2.6px !important; opacity: .96; }
    svg polygon.diagram-code-link-connector { fill: var(--diagram-link) !important; }
    svg .diagram-code-link-badge { cursor: pointer; }
    svg .diagram-code-link-badge rect { fill: var(--diagram-link-bg); stroke: var(--diagram-link); stroke-width: 1.4px; rx: 5px; ry: 5px; filter: drop-shadow(0 1px 2px rgba(15,23,42,.18)); }
    svg .diagram-code-link-badge text { fill: var(--diagram-link); font: 700 11px ui-monospace, SFMono-Regular, Consolas, monospace; text-anchor: middle; dominant-baseline: central; pointer-events: none; }
    svg .diagram-code-link-badge.diagram-code-link-hover rect { fill: var(--diagram-link-hover-bg); stroke: var(--diagram-focus); }
    svg .diagram-code-link-badge.diagram-code-link-hover text { fill: var(--diagram-focus); }
    svg .diagram-code-link-active { filter: drop-shadow(0 0 3px rgba(4,120,87,.65)); }
    svg .asset-focus-connector.diagram-code-link-connector { stroke: var(--diagram-focus) !important; stroke-width: 3px !important; opacity: .95; }
    svg polygon.asset-focus-connector.diagram-code-link-connector { fill: var(--diagram-focus) !important; }
    svg text.asset-focus-match.diagram-code-link-target, svg tspan.asset-focus-match.diagram-code-link-target { fill: var(--diagram-focus) !important; stroke: none !important; }
    svg .asset-focus-related-hover { stroke: var(--diagram-focus) !important; fill: var(--diagram-focus) !important; opacity: 1 !important; filter: none; }
    svg text.asset-focus-related-hover, svg tspan.asset-focus-related-hover { fill: var(--diagram-focus) !important; stroke: none !important; }
    svg .asset-search-match { fill: #cf222e !important; stroke: none !important; }
    svg .asset-search-submatch { fill: transparent; stroke: #ff4d5e; stroke-width: 2px; vector-effect: non-scaling-stroke; opacity: .98; }
    svg .asset-search-current { fill: #ff2a3d !important; stroke: none !important; filter: none; font-weight: 800 !important; text-decoration: underline; text-decoration-thickness: 2px; text-underline-offset: 3px; }
    svg text.asset-search-current, svg tspan.asset-search-current { fill: #ff2a3d !important; stroke: none !important; filter: none; font-weight: 800 !important; text-decoration: underline; text-decoration-thickness: 2px; text-underline-offset: 3px; }
    @keyframes focus-dash-flow { from { stroke-dashoffset: 0; } to { stroke-dashoffset: -16; } }
    @keyframes focus-dash-flow-reverse { from { stroke-dashoffset: 0; } to { stroke-dashoffset: 16; } }
    @media (prefers-reduced-motion: reduce) {
      svg line.asset-focus-connector, svg path.asset-focus-connector, svg polyline.asset-focus-connector, svg polygon.asset-focus-connector, svg .asset-focus-object, svg .asset-focus-match { animation: none; }
    }
"""


def plantuml_preview_svg(svg: str, theme: str) -> str:
    colors = PLANTUML_PREVIEW_THEMES[theme if theme in PLANTUML_PREVIEW_THEMES else "light"]
    style = _plantuml_preview_style(colors)
    return re.sub(r"(<svg\b[^>]*>)", r"\1" + style, svg, count=1, flags=re.IGNORECASE)


def _plantuml_preview_style(colors: dict[str, str]) -> str:
    return f"""
<style>
svg {{ background: {colors["bg"]} !important; }}
svg text:not(.diagram-note-text):not(.diagram-note-marker-text):not(.diagram-code-link-badge-text):not(.asset-focus-match):not(.asset-focus-related-hover),
svg tspan:not(.diagram-note-text):not(.diagram-note-marker-text):not(.asset-focus-match):not(.asset-focus-related-hover) {{ fill: {colors["text"]} !important; stroke: none !important; }}
svg line:not(.asset-focus-connector):not(.diagram-code-link-connector):not(.diagram-note-link),
svg path:not(.asset-focus-object):not(.asset-focus-connector):not(.diagram-note-box):not(.diagram-note-link):not(.diagram-code-link-connector),
svg polyline:not(.asset-focus-connector):not(.diagram-code-link-connector) {{ stroke: {colors["line"]} !important; }}
svg polygon:not(.asset-focus-connector):not(.asset-focus-object):not(.diagram-code-link-connector):not([fill="#FFFFFF"]):not([fill="#FEFECE"]):not([fill="#EEEEEE"]):not([fill="#2D2D30"]):not([fill="#252526"]):not([fill="#3B3216"]):not([fill="#FBFB77"]) {{ fill: {colors["arrow"]} !important; stroke: {colors["arrow"]} !important; stroke-width: 1.4px !important; }}
svg polygon[fill="#FFFFFF"]:not(.asset-focus-object),
svg polygon[fill="#FEFECE"]:not(.asset-focus-object),
svg polygon[fill="#EEEEEE"]:not(.asset-focus-object),
svg polygon[fill="#2D2D30"]:not(.asset-focus-object),
svg polygon[fill="#252526"]:not(.asset-focus-object),
svg path[fill="#FFFFFF"]:not(.asset-focus-object),
svg path[fill="#FEFECE"]:not(.asset-focus-object),
svg path[fill="#2D2D30"]:not(.asset-focus-object),
svg rect:not(.diagram-note-box):not(.diagram-code-link-badge-box),
svg ellipse[fill="#FFFFFF"]:not(.asset-focus-object),
svg circle:not(.asset-focus-object) {{ fill: {colors["box"]} !important; stroke: {colors["line"]} !important; }}
svg ellipse[fill="#D4D4D4"]:not(.asset-focus-object),
svg polygon[fill="#D4D4D4"]:not(.asset-focus-object) {{ fill: {colors["arrow"]} !important; stroke: {colors["arrow"]} !important; }}
svg path[fill="#FBFB77"],
svg polygon[fill="#FBFB77"],
svg rect[fill="#FBFB77"],
svg path[fill="#3B3216"],
svg polygon[fill="#3B3216"],
svg rect[fill="#3B3216"] {{ fill: {colors["note"]} !important; stroke: {colors["note_border"]} !important; }}
</style>
"""

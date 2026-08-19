from __future__ import annotations

import html

from .assets_styles import stylesheet


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _report_logo_svg() -> str:
    return """<svg class="report-brand-logo" viewBox="0 0 160 160" role="img" aria-label="Agent Workspace">
  <defs>
    <radialGradient id="aw-bg-glow" cx="50%" cy="48%" r="72%">
      <stop offset="0" stop-color="#123241"/>
      <stop offset=".58" stop-color="#071019"/>
      <stop offset="1" stop-color="#020407"/>
    </radialGradient>
    <linearGradient id="aw-cyan" x1="24" y1="24" x2="136" y2="136">
      <stop offset="0" stop-color="#eaffff"/>
      <stop offset=".5" stop-color="#27f0f4"/>
      <stop offset="1" stop-color="#0ea5e9"/>
    </linearGradient>
    <linearGradient id="aw-amber" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#ffe66d"/>
      <stop offset="1" stop-color="#f59e0b"/>
    </linearGradient>
    <filter id="aw-cyan-glow" x="-35%" y="-35%" width="170%" height="170%">
      <feGaussianBlur stdDeviation="3.2" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <filter id="aw-soft-shadow" x="-25%" y="-25%" width="150%" height="150%">
      <feDropShadow dx="0" dy="10" stdDeviation="10" flood-color="#000" flood-opacity=".48"/>
    </filter>
  </defs>
  <rect x="4" y="4" width="152" height="152" rx="30" fill="url(#aw-bg-glow)" filter="url(#aw-soft-shadow)"/>
  <path d="M20 72h18M122 82h18M80 122v18" stroke="url(#aw-cyan)" stroke-width="5" stroke-linecap="round" opacity=".78" filter="url(#aw-cyan-glow)"/>
  <path d="M31 94h-13v-18" stroke="url(#aw-cyan)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" opacity=".85" filter="url(#aw-cyan-glow)"/>
  <path d="M30 72h-14v-18" stroke="url(#aw-amber)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" opacity=".9" filter="url(#aw-cyan-glow)"/>
  <circle cx="18" cy="54" r="9" fill="#150a02" stroke="url(#aw-amber)" stroke-width="5" filter="url(#aw-cyan-glow)"/>
  <circle cx="18" cy="94" r="9" fill="#031719" stroke="url(#aw-cyan)" stroke-width="5" filter="url(#aw-cyan-glow)"/>
  <circle cx="80" cy="142" r="9" fill="#150a02" stroke="url(#aw-amber)" stroke-width="5" filter="url(#aw-cyan-glow)"/>
  <rect x="34" y="31" width="92" height="92" rx="18" fill="#071018" stroke="#273642" stroke-width="8"/>
  <rect x="40" y="37" width="80" height="80" rx="14" fill="#081923" stroke="url(#aw-cyan)" stroke-width="5" filter="url(#aw-cyan-glow)"/>
  <circle cx="58" cy="53" r="5" fill="#f59e0b"/>
  <circle cx="73" cy="53" r="5" fill="#22d3ee"/>
  <circle cx="88" cy="53" r="5" fill="#22d3ee"/>
  <text x="80" y="90" text-anchor="middle" fill="#bffcff" font-family="ui-monospace, SFMono-Regular, Consolas, monospace" font-size="34" font-weight="900" filter="url(#aw-cyan-glow)">AW</text>
  <path d="M55 100l9 7-9 7M72 113h15" stroke="#22d3ee" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" filter="url(#aw-cyan-glow)"/>
</svg>"""


def html_header(title: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_esc(title)}</title>
  <script>
    (function () {{
      try {{
        const key = "codex-diff-report-theme";
        const stored = localStorage.getItem(key);
        const fallback = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
        document.documentElement.dataset.theme = stored === "dark" || stored === "light" ? stored : fallback;
      }} catch (error) {{
        document.documentElement.dataset.theme = "light";
      }}
    }}());
  </script>
  <style>
{stylesheet()}  </style>
</head>
<body>
<div class="report-brand" aria-hidden="true"><div class="report-brand-inner"><span class="report-brand-mark">{_report_logo_svg()}</span><span class="report-brand-text"><span class="report-brand-title">Report</span></span></div></div>
<div class="settings-modal" data-settings-modal hidden>
  <div class="settings-backdrop" data-settings-close></div>
  <div class="settings-dialog" role="dialog" aria-modal="true" aria-labelledby="settings-title">
    <div class="settings-dialog-head">
      <h2 id="settings-title">Settings</h2>
      <button type="button" class="settings-close" data-settings-close aria-label="Close settings">&times;</button>
    </div>
    <div class="settings-menu">
      <div class="settings-group">
        <div class="settings-label">Theme</div>
        <div class="settings-options">
          <button type="button" class="settings-option" data-theme-value="light">Light</button>
          <button type="button" class="settings-option" data-theme-value="dark">Dark</button>
        </div>
      </div>
      <div class="settings-group">
        <div class="settings-label">Text scale</div>
        <div class="settings-scale-controls">
          <button type="button" class="settings-scale-button" data-text-scale-step="-0.1" aria-label="Decrease text scale">-</button>
          <button type="button" class="settings-scale-value" data-text-scale-reset aria-label="Reset text scale">100%</button>
          <button type="button" class="settings-scale-button" data-text-scale-step="0.1" aria-label="Increase text scale">+</button>
        </div>
      </div>
    </div>
  </div>
</div>
<div class="copy-context-menu" data-copy-markdown-menu hidden>
  <button type="button" data-copy-plain-action>Copy</button>
  <button type="button" data-copy-markdown-action>Copy as Markdown</button>
</div>
"""

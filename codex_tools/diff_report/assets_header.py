from __future__ import annotations

import html

from .assets_styles import stylesheet


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


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
<div class="report-brand" aria-hidden="true"><div class="report-brand-inner"><span class="report-brand-mark">AI</span><span class="report-brand-text"><span class="report-brand-title">Diff</span><span class="report-brand-subtitle">report</span></span></div></div>
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

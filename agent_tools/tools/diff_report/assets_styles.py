from __future__ import annotations

from .assets_plantuml_svg import plantuml_svg_styles


def stylesheet() -> str:
    return """    :root {
      color-scheme: light;
      --bg: #f3f3f3;
      --panel: #fbfbfc;
      --card-bg: var(--panel);
      --panel-subtle: #f1f3f6;
      --meta-panel: #f7f8fa;
      --meta-border: #b8c0ca;
      --meta-label: #57606a;
      --meta-text: #1f1f1f;
      --story-step-bg: #f6f8fa;
      --story-step-border: #8c959f;
      --story-step-hover-bg: #eef6ff;
      --story-step-active-bg: #dbeafe;
      --story-step-active-border: #0969da;
      --stat-add: #1a7f37;
      --stat-del: #cf222e;
      --border: #b8c0ca;
      --text: #1f1f1f;
      --muted: #616161;
      --font-stack: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --link: #007acc;
      --button-bg: #ffffff;
      --button-hover-bg: #e5f1fb;
      --settings-active-bg: #e5f1fb;
      --settings-active-text: #0969da;
      --row-bg: #fbfbfc;
      --header-bg: #e9edf2;
      --add-bg: #dff2e6;
      --del-bg: #f9d9de;
      --hunk-bg: #dbeafe;
      --hunk-text: #0969da;
      --comment-bg: #fff3c4;
      --comment-border: #ca5010;
      --comment-target-ctx-bg: #f4f6f4;
      --comment-target-add-bg: #d6eedc;
      --comment-target-del-bg: #f8d5da;
      --comment-target-overlay: rgba(202,80,16,.045);
      --comment-title-bg: rgba(255,255,255,.44);
      --comment-title-border: rgba(202,80,16,.34);
      --comment-panel-border: rgba(202,80,16,.55);
      --code-bg: #eef2f6;
      --brand-panel: rgba(251,251,252,.94);
      --brand-text: #1f1f1f;
      --shadow: rgba(0,0,0,.16);
      --diagram-bg: #ffffff;
      --diagram-code-context-bg: rgba(255,244,206,.46);
      --diagram-code-target-bg: rgba(255,232,166,.9);
      --diagram-code-target-border: #ca5010;
      --diagram-code-file: #0969da;
      --diagram-focus: #52657f;
      --diagram-focus-glow: rgba(82,101,127,.32);
      --diagram-link: #107c10;
      --diagram-link-bg: #e9f5e9;
      --diagram-link-hover-bg: #deecf9;
      --diagram-svg-filter: none;
      --diagram-svg-bg: #ffffff;
      --diagram-svg-text: #111827;
      --diagram-svg-line: #475569;
      --diagram-svg-arrow: #334155;
      --diagram-svg-box-bg: #ffffff;
      --diagram-svg-note-bg: #fff8c5;
      --diagram-note-bg: #dbeafe;
      --diagram-note-hover-bg: #bfdbfe;
      --diagram-note-text: #111827;
      --diagram-note-link: #2563eb;
      --diagram-note-marker-bg: #eff6ff;
      --graph-bg: #f8fafc;
      --graph-node-bg: #ffffff;
      --graph-node-border: #94a3b8;
      --graph-node-text: #111827;
      --graph-domain-bg: #e0f2fe;
      --graph-artifact-bg: #f1f5f9;
      --graph-edge: #64748b;
      --graph-focus: #2563eb;
      --graph-active: #0f766e;
      --graph-status-pass-bg: #f0fdf4;
      --graph-status-pass-border: #16a34a;
      --graph-status-risk-bg: #fffbeb;
      --graph-status-risk-border: #d97706;
      --graph-status-fail-bg: #fef2f2;
      --graph-status-fail-border: #dc2626;
      --graph-status-info-bg: #f5f3ff;
      --graph-status-info-border: #7c3aed;
      --graph-status-auto-pass-bg: #eff6ff;
      --graph-status-auto-pass-border: #2563eb;
      --graph-status-neutral-bg: #f8fafc;
      --graph-status-neutral-border: #64748b;
      --graph-isolated-option-text: #475569;
      --graph-isolated-option-bg: #e8edf3;
      --overlay-bg: rgba(31,35,40,.42);
      --page-gutter: 8px;
      --nav-width: 430px;
      --brand-height: 250px;
      --brand-top-padding: 16px;
      --brand-scale: 1;
      --brand-mark-size: 172px;
      --brand-title-size: 80px;
      --brand-subtitle-size: 40px;
      --brand-gap: 20px;
      --brand-padding-x: 20px;
      --settings-top: calc(var(--page-gutter) + var(--brand-height) - 44px);
      --review-nav-top: calc(var(--page-gutter) + var(--brand-height) + 12px);
      --left-chrome-x: calc(var(--page-gutter) + 34px);
      --left-chrome-width: calc(var(--nav-width) - 68px);
      --story-offset: 0px;
      --story-nav-height: 76px;
      --text-scale: 1;
      --screen-body-font: 18px;
      --screen-code-font: 15px;
      --scaled-body-font: calc(var(--screen-body-font) * var(--text-scale));
      --scaled-code-font: calc(var(--screen-code-font) * var(--text-scale));
      --diff-num-width: 64px;
      --comment-gutter-width: 112px;
      --content-width: 1260px;
      --floating-control-size: 44px;
      --floating-control-gap: 18px;
      --floating-bottom-gap: 8px;
      --floating-content-gutter: max(24px, calc((100vw - var(--nav-width) - var(--content-width)) / 2));
    }
    :root[data-theme="dark"] {
      color-scheme: dark;
      --bg: #1e1e1e;
      --panel: #252526;
      --card-bg: var(--panel);
      --panel-subtle: #2d2d30;
      --meta-panel: #1b1b1d;
      --meta-border: #52525a;
      --meta-label: #a7a7ad;
      --meta-text: #f0f0f0;
      --story-step-bg: #1b1b1d;
      --story-step-border: #5f6368;
      --story-step-hover-bg: #1f3447;
      --story-step-active-bg: #15395b;
      --story-step-active-border: #58a6ff;
      --stat-add: #7ee787;
      --stat-del: #ff7b72;
      --border: #3c3c3c;
      --text: #d4d4d4;
      --muted: #858585;
      --font-stack: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --link: #3794ff;
      --button-bg: #2d2d30;
      --button-hover-bg: #094771;
      --settings-active-bg: #0e639c;
      --settings-active-text: #ffffff;
      --row-bg: #1e1e1e;
      --header-bg: #252526;
      --add-bg: #113311;
      --del-bg: #3f1d1d;
      --hunk-bg: #063b49;
      --hunk-text: #79c0ff;
      --comment-bg: #3a3217;
      --comment-border: #cca700;
      --comment-target-ctx-bg: #25251f;
      --comment-target-add-bg: #14351f;
      --comment-target-del-bg: #421f24;
      --comment-target-overlay: rgba(204,167,0,.08);
      --comment-title-bg: rgba(255,255,255,.06);
      --comment-title-border: rgba(204,167,0,.34);
      --comment-panel-border: rgba(204,167,0,.55);
      --code-bg: #1e1e1e;
      --brand-panel: rgba(37,37,38,.94);
      --brand-text: #d4d4d4;
      --shadow: rgba(0,0,0,.45);
      --diagram-bg: #1e1e1e;
      --diagram-code-context-bg: rgba(55,65,81,.55);
      --diagram-code-target-bg: rgba(14,99,156,.5);
      --diagram-code-target-border: #3794ff;
      --diagram-code-file: #9cdcfe;
      --diagram-focus: #9cdcfe;
      --diagram-focus-glow: rgba(156,220,254,.42);
      --diagram-link: #4ec9b0;
      --diagram-link-bg: #173f3a;
      --diagram-link-hover-bg: #094771;
      --diagram-svg-filter: none;
      --diagram-svg-bg: #1f1f1f;
      --diagram-svg-text: #d4d4d4;
      --diagram-svg-line: #c5c5c5;
      --diagram-svg-arrow: #f0f6fc;
      --diagram-svg-box-bg: #252526;
      --diagram-svg-note-bg: #3a3217;
      --diagram-note-bg: #1f2f46;
      --diagram-note-hover-bg: #094771;
      --diagram-note-text: #d4d4d4;
      --diagram-note-link: #3794ff;
      --diagram-note-marker-bg: #173f5f;
      --graph-bg: #161b22;
      --graph-node-bg: #21262d;
      --graph-node-border: #6e7681;
      --graph-node-text: #f0f6fc;
      --graph-domain-bg: #0f2f4a;
      --graph-artifact-bg: #262c36;
      --graph-edge: #8b949e;
      --graph-focus: #58a6ff;
      --graph-active: #39c5bb;
      --graph-status-pass-bg: #12331f;
      --graph-status-pass-border: #7ee787;
      --graph-status-risk-bg: #332b13;
      --graph-status-risk-border: #d6b73d;
      --graph-status-fail-bg: #3d171d;
      --graph-status-fail-border: #ff7b72;
      --graph-status-info-bg: #281f45;
      --graph-status-info-border: #c4b5fd;
      --graph-status-auto-pass-bg: #102a43;
      --graph-status-auto-pass-border: #58a6ff;
      --graph-status-neutral-bg: #20242c;
      --graph-status-neutral-border: #a8b3c2;
      --graph-isolated-option-text: #a8b3c2;
      --graph-isolated-option-bg: #20242c;
      --overlay-bg: rgba(0,0,0,.68);
    }
    * { box-sizing: border-box; }
    html { scrollbar-gutter: stable; }
    body { margin: 0; padding-bottom: var(--story-nav-height); background: var(--bg); color: var(--text); font: var(--scaled-body-font)/1.52 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body.story-nav-hidden { --story-nav-height: 0px; --floating-bottom-gap: 24px; }
    main { width: calc(100% - var(--nav-width) - (var(--page-gutter) * 3)); max-width: calc(100% - var(--nav-width) - (var(--page-gutter) * 3)); min-width: 0; margin: var(--page-gutter) var(--page-gutter) calc(16px + var(--story-nav-height)) calc(var(--nav-width) + (var(--page-gutter) * 2)); }
    .report-brand { position: fixed; left: var(--page-gutter); top: var(--page-gutter); z-index: 12; display: flex; align-items: center; justify-content: center; width: var(--nav-width); height: var(--brand-height); padding-top: 0; overflow: hidden; pointer-events: none; color: var(--brand-text); }
    .report-brand::before { content: ""; position: absolute; inset: 0; height: var(--brand-height); border-radius: 10px; background: var(--brand-panel); box-shadow: 0 10px 24px var(--shadow); }
    .report-brand-inner { position: relative; display: grid; grid-template-columns: var(--brand-mark-size) max-content; align-items: center; justify-content: center; gap: var(--brand-gap); width: 430px; max-width: none; min-height: 0; padding: 16px var(--brand-padding-x); transform: scale(var(--brand-scale)); transform-origin: center; font-weight: 800; letter-spacing: 0; }
    .report-brand-mark { display: flex; align-items: center; justify-content: center; width: var(--brand-mark-size); height: var(--brand-mark-size); border-radius: 28px; overflow: visible; color: #22d3ee; filter: drop-shadow(0 10px 20px rgba(0,0,0,.34)); }
    .report-brand-logo { display: block; width: 100%; height: 100%; overflow: visible; }
    .report-brand-text { display: grid; gap: 2px; min-width: 0; line-height: 1.05; }
    .report-brand-title { color: var(--brand-text); font-size: calc(var(--brand-title-size) * .62); font-weight: 850; white-space: nowrap; text-shadow: 0 2px 10px var(--shadow); }
    .report-brand-subtitle { color: var(--muted); font-size: var(--brand-subtitle-size); white-space: nowrap; }
    body.has-diagram-open .report-brand { z-index: 9; }
    .settings-launcher { position: fixed; right: max(8px, calc(var(--floating-content-gutter) - var(--floating-control-size) - var(--floating-control-gap))); bottom: calc(var(--story-nav-height) + var(--floating-bottom-gap)); z-index: 32; width: auto; opacity: 1; visibility: visible; pointer-events: auto; transform: translateY(0) scale(1); transition: opacity .18s ease, transform .18s ease, visibility 0s linear .18s, border-color .12s ease, box-shadow .12s ease; }
    .settings-toggle { display: inline-flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; width: var(--floating-control-size); height: var(--floating-control-size); padding: 0; border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--link); box-shadow: 0 10px 28px var(--shadow); cursor: pointer; font: 800 18px/1 ui-monospace, SFMono-Regular, Consolas, monospace; }
    .settings-toggle span, .settings-toggle::before, .settings-toggle::after { content: ""; display: block; width: 18px; height: 2px; border-radius: 99px; background: currentColor; }
    .settings-toggle:hover { border-color: var(--link); box-shadow: 0 12px 32px rgba(9,105,218,.22); }
    .settings-modal[hidden] { display: none; }
    .settings-modal { position: fixed; inset: 0; z-index: 1100; }
    .settings-backdrop { position: absolute; inset: 0; background: var(--overlay-bg); }
    .settings-dialog { position: absolute; left: 50%; top: 50%; display: grid; gap: 18px; width: min(460px, calc(100vw - 40px)); max-height: calc(100vh - 40px); overflow: auto; transform: translate(-50%, -50%); padding: 20px; border: 1px solid var(--border); border-radius: 8px; background: var(--panel); color: var(--text); box-shadow: 0 18px 58px rgba(0,0,0,.42); font-size: var(--screen-body-font); }
    .settings-dialog-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .settings-dialog h2 { margin: 0; color: var(--text); font-size: 20px; }
    .settings-close { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; padding: 0; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); cursor: pointer; font: 22px/1 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    .settings-close:hover { border-color: var(--link); color: var(--link); }
    .settings-menu { display: grid; gap: 12px; }
    .settings-group { display: grid; gap: 6px; }
    .settings-label { color: var(--meta-label); font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: .04em; }
    .settings-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
    .settings-option { display: inline-flex; align-items: center; justify-content: center; min-width: 0; height: 34px; padding: 0 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); cursor: pointer; font: 700 15px/1 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    .settings-option:hover { border-color: var(--link); color: var(--link); }
    .settings-option.is-active { border-color: var(--link); background: var(--settings-active-bg); color: var(--settings-active-text); box-shadow: inset 3px 0 0 var(--link); }
    .settings-scale-controls { display: grid; grid-template-columns: 40px minmax(0, 1fr) 40px; gap: 8px; align-items: center; }
    .settings-scale-value { display: inline-flex; align-items: center; justify-content: center; min-width: 0; height: 34px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); font: 700 14px/1 ui-monospace, SFMono-Regular, Consolas, monospace; }
    .settings-scale-button { display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 34px; padding: 0; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--link); cursor: pointer; font: 800 18px/1 ui-monospace, SFMono-Regular, Consolas, monospace; }
    .settings-scale-button:hover { border-color: var(--link); background: var(--button-hover-bg); }
    .settings-scale-button:disabled { cursor: default; opacity: .45; border-color: var(--border); background: var(--button-bg); color: var(--muted); }
    .copy-context-menu[hidden] { display: none; }
    .copy-context-menu { position: fixed; z-index: 1200; min-width: 178px; padding: 6px; border: 1px solid var(--border); border-radius: 8px; background: var(--panel); box-shadow: 0 12px 32px var(--shadow); }
    .copy-context-menu button { display: flex; align-items: center; justify-content: flex-start; width: 100%; min-height: 32px; padding: 0 10px; border: 0; border-radius: 6px; background: transparent; color: var(--text); cursor: pointer; font: 700 14px/1.2 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; text-align: left; }
    .copy-context-menu button:hover, .copy-context-menu button:focus-visible { background: var(--button-hover-bg); color: var(--link); outline: none; }
    header, section, .file { width: min(100%, var(--content-width)); max-width: 100%; min-width: 0; margin-right: auto; margin-left: auto; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 16px; }
    .file { border-top: 0; }
    header, section { padding: 20px; }
    h1, h2 { margin: 0 0 12px; line-height: 1.2; }
    h1 { font-size: 28px; }
    h2 { font-size: 20px; }
    p { margin: 0 0 10px; }
    .vocabulary-ref-wrap { position: relative; display: inline-flex; align-items: baseline; max-width: 100%; vertical-align: baseline; }
    .vocabulary-ref { display: inline-flex; align-items: center; justify-content: center; min-width: 0; max-width: 100%; padding: 1px 5px; border: 0; border-bottom: 1px dotted color-mix(in srgb, var(--link) 78%, var(--text)); border-radius: 4px; background: color-mix(in srgb, var(--button-hover-bg) 24%, transparent); color: var(--link); cursor: help; font: inherit; line-height: inherit; text-align: inherit; overflow-wrap: anywhere; transition: background .12s ease, box-shadow .12s ease, color .12s ease; }
    .vocabulary-ref:hover, .vocabulary-ref:focus-visible { outline: none; border-color: var(--link); background: var(--button-hover-bg); color: var(--link); }
    .vocabulary-popover { position: absolute; left: 0; top: calc(100% + 8px); z-index: 80; box-sizing: border-box; display: grid; gap: 5px; width: min(360px, calc(100vw - 32px)); max-width: calc(100vw - 32px); padding: 10px 12px; border: 1px solid var(--comment-panel-border); border-left: 4px solid var(--comment-border); border-radius: 6px; background: var(--comment-bg); color: var(--text); box-shadow: 0 12px 30px var(--shadow); font: var(--scaled-code-font)/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; opacity: 0; visibility: hidden; pointer-events: none; user-select: text; transform: translateY(4px); transition: opacity .14s ease, transform .14s ease, visibility 0s linear .14s; }
    .vocabulary-ref-wrap.is-positioned .vocabulary-popover { position: fixed; left: var(--vocabulary-popover-left, 16px); top: var(--vocabulary-popover-top, 16px); right: auto; z-index: 1010; width: min(360px, calc(100vw - 32px)); }
    .vocabulary-popover strong { font-size: 1.08em; }
    .vocabulary-aliases { color: var(--muted); font-size: .92em; }
    .vocabulary-ref-wrap.is-open .vocabulary-ref { background: color-mix(in srgb, var(--comment-bg) 74%, var(--button-hover-bg)); box-shadow: 0 0 0 2px color-mix(in srgb, var(--comment-border) 28%, transparent); color: var(--link); }
    .vocabulary-ref-wrap.is-open .vocabulary-popover { opacity: 1; visibility: visible; pointer-events: auto; transform: translateY(0); transition-delay: 0s; }
    .review-summary-blocks { display: grid; gap: 12px; }
    .review-summary { white-space: pre-line; overflow-wrap: anywhere; font-size: calc(var(--scaled-code-font) * 1.16); line-height: 1.58; }
    .review-summary-blocks .review-summary { margin: 0; }
    .summary-artifact-preview .diagram-preview-wrap { margin-top: 0; }
    .summary-artifact-preview .diagram-preview { width: min(760px, 100%); }
    .summary-artifact-preview .diagram-preview-canvas { height: clamp(220px, 26vw, 320px); }
    body:has(.general-report) { --brand-height: 110px; --brand-mark-size: 74px; --brand-title-size: 54px; --brand-subtitle-size: 28px; }
    .report-note, .review-summary { display: block; width: 100%; max-width: 100%; min-width: 0; margin: 0; padding: 12px; border: 1px solid var(--meta-border); border-radius: 6px; background: var(--meta-panel); color: var(--meta-text); white-space: pre-wrap; overflow-wrap: anywhere; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }
    .report-note { max-width: 100%; }
    .diff-stats { display: grid; gap: 10px; }
    .diff-stats-row { display: grid; gap: 10px; }
    .diff-stats-lines { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .diff-stats-files { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .diff-stats-row div { min-width: 0; max-width: 100%; padding: 12px; border: 1px solid var(--meta-border); border-radius: 6px; background: var(--meta-panel); color: var(--meta-text); overflow-wrap: anywhere; }
    .diff-stats .label { font-size: .86rem; }
    .diff-stats strong { display: block; margin-top: 4px; font: 800 calc(var(--scaled-code-font) * 1.08)/1.2 ui-monospace, SFMono-Regular, Consolas, monospace; }
    .diff-stat-add { color: var(--stat-add); }
    .diff-stat-del { color: var(--stat-del); }
    .general-report section { overflow: hidden; }
    .general-report .report-table-section { overflow: visible; }
    .review-summary-links { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0 0; padding: 0; list-style: none; }
    .review-summary-links a { display: inline-flex; align-items: center; min-height: 32px; padding: 0 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--link); font-weight: 750; text-decoration: none; }
    .review-summary-links a:hover { border-color: var(--link); background: var(--button-hover-bg); }
    .report-metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
    .report-card-grid { display: grid; grid-template-columns: 1fr; gap: 12px; }
    .report-metric, .report-card, .report-artifact { min-width: 0; border: 1px solid var(--meta-border); border-radius: 8px; background: var(--meta-panel); color: var(--meta-text); }
    .report-metric { display: grid; gap: 6px; padding: 14px; border-left: 5px solid var(--meta-border); }
    .report-metric strong { font: 850 calc(var(--scaled-body-font) * 1.55)/1.05 ui-monospace, SFMono-Regular, Consolas, monospace; overflow-wrap: anywhere; }
    .report-metric-note { color: var(--muted); font-size: .92em; overflow-wrap: anywhere; }
    .report-card { display: grid; gap: 12px; padding: 14px; border-left: 5px solid var(--meta-border); }
    .report-card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; min-width: 0; }
    .report-card-group-title { grid-column: 1 / -1; margin: 6px 0 0; color: var(--muted); font: 850 .86rem/1.2 ui-monospace, SFMono-Regular, Consolas, monospace; letter-spacing: .04em; text-transform: uppercase; }
    .report-card h3 { min-width: 0; margin: 0; font-size: calc(var(--scaled-body-font) * 1.05); overflow-wrap: break-word; }
    .report-card-body { color: var(--meta-text); white-space: pre-line; overflow-wrap: break-word; }
    .report-card-metrics { display: grid; grid-template-columns: 1fr; gap: 6px; }
    .report-card-metrics > span { display: grid; grid-template-columns: minmax(220px, .92fr) minmax(260px, 1.08fr); gap: 12px; align-items: baseline; min-width: 0; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--panel); overflow-wrap: break-word; }
    .report-card-metrics .label { margin: 0; color: var(--text); font: 500 .82em/1.35 ui-monospace, SFMono-Regular, Consolas, monospace; }
    .report-card-metrics strong { display: block; min-width: 0; font: 500 .82em/1.35 ui-monospace, SFMono-Regular, Consolas, monospace; overflow-wrap: anywhere; }
    .report-card-metric-parts { display: flex; flex-wrap: wrap; gap: 4px 8px; align-items: baseline; }
    .report-card-metric-part { display: inline-flex; gap: 4px; align-items: baseline; min-width: 0; white-space: nowrap; }
    .report-card-metric-separator { color: var(--muted); font-weight: 650; }
    .report-card-metric-part-label, .report-card-metric-part-value { font: inherit; font-weight: inherit; }
    .report-card-metric-part.status-covered, .report-card-metric-part.status-covered-candidate, .report-card-metric-part.status-pass, .report-card-metric-part.status-not-failed { color: var(--stat-add); }
    .report-card-metric-part.status-risk, .report-card-metric-part.status-not-applicable-candidate, .report-card-metric-part.status-warning, .report-card-metric-part.status-assumption-failure, .report-card-metric-part.status-skip, .report-card-metric-part.status-skipped, .report-card-metric-part.status-auto-warning-candidate { color: var(--comment-border); }
    .report-card-metric-part.status-gap, .report-card-metric-part.status-fail, .report-card-metric-part.status-blocked, .report-card-metric-part.status-needs-evidence, .report-card-metric-part.status-auto-fail-candidate { color: var(--stat-del); }
    .report-card-metric-part.status-auto-pass-candidate { color: var(--graph-status-auto-pass-border); }
    .report-card-metric-part.status-not-started, .report-card-metric-part.status-not-run, .report-card-metric-part.status-not-done, .report-card-metric-part.status-other, .report-card-metric-part.status-unknown, .report-card-metric-part.status-auto-no-result-candidate { color: var(--muted); }
    .report-card-table-stack { display: grid; gap: 10px; min-width: 0; }
    .report-card-table-wrap { min-width: 0; overflow-x: auto; border: 1px solid var(--border); border-radius: 6px; background: var(--panel); }
    .report-card-table-wrap h4 { margin: 0; padding: 8px 10px; border-bottom: 1px solid var(--border); font-size: .86em; }
    .report-card-table-note { margin: 0; padding: 0 10px 8px; color: var(--muted); font-size: .82em; }
    .report-card-table { width: max-content; min-width: 100%; border-collapse: collapse; table-layout: auto; font: 500 .82em/1.35 ui-monospace, SFMono-Regular, Consolas, monospace; }
    .report-card-table th, .report-card-table td { padding: 7px 10px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; white-space: nowrap; }
    .report-card-table th, .report-card-table td { min-width: 120px; }
    .report-card-table th:first-child, .report-card-table td:first-child { min-width: 270px; }
    .report-card-table thead th { color: var(--text); background: var(--meta-panel); font-weight: 650; }
    .report-card-table tbody tr:last-child th, .report-card-table tbody tr:last-child td { border-bottom: 0; }
    .report-card-table tbody th { color: var(--text); font-weight: 600; }
    .report-card-table .report-metric-cell-link { font: inherit; font-weight: inherit; }
    .report-card-table tbody th.status-covered, .report-card-table tbody th.status-covered-candidate, .report-card-table tbody th.status-pass, .report-card-table tbody th.status-not-failed, .report-card-table tbody td.status-covered, .report-card-table tbody td.status-covered-candidate, .report-card-table tbody td.status-pass, .report-card-table tbody td.status-not-failed { background: color-mix(in srgb, var(--add-bg) 70%, var(--panel)); color: var(--stat-add); }
    .report-card-table tbody td.status-risk, .report-card-table tbody td.status-warning, .report-card-table tbody td.status-assumption-failure, .report-card-table tbody td.status-skip, .report-card-table tbody td.status-skipped, .report-card-table tbody td.status-auto-warning-candidate { background: color-mix(in srgb, var(--comment-bg) 70%, var(--panel)); color: var(--comment-border); }
    .report-card-table tbody td.status-gap, .report-card-table tbody td.status-fail, .report-card-table tbody td.status-blocked, .report-card-table tbody td.status-needs-evidence, .report-card-table tbody td.status-auto-fail-candidate { background: color-mix(in srgb, var(--del-bg) 70%, var(--panel)); color: var(--stat-del); }
    .report-card-table tbody td.status-auto-pass-candidate { background: color-mix(in srgb, var(--graph-status-auto-pass-bg) 70%, var(--panel)); color: var(--graph-status-auto-pass-border); }
    .report-card-table tbody td.status-not-run, .report-card-table tbody td.status-not-done, .report-card-table tbody td.status-not-started, .report-card-table tbody td.status-other, .report-card-table tbody td.status-unknown, .report-card-table tbody td.status-auto-no-result-candidate { background: color-mix(in srgb, var(--graph-status-neutral-border) 22%, var(--panel)); color: var(--muted); }
    .report-card-links { display: flex; flex-wrap: wrap; gap: 8px; }
    .report-card-links a, .report-artifact { color: var(--link); text-decoration: none; }
    .report-card-links a { display: inline-flex; align-items: center; min-height: 30px; padding: 0 9px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); font-weight: 700; }
    .report-card-links a:hover, .report-artifact:hover { border-color: var(--link); background: var(--button-hover-bg); }
    .report-status-badge { display: inline-flex; align-items: center; justify-content: center; min-height: 26px; padding: 3px 9px; border: 1px solid var(--meta-border); border-radius: 999px; background: var(--button-bg); color: var(--meta-text); font: 800 13px/1.1 ui-monospace, SFMono-Regular, Consolas, monospace; white-space: nowrap; }
    .status-covered, .status-covered-candidate, .status-pass, .status-not-failed { border-color: color-mix(in srgb, var(--stat-add) 70%, var(--meta-border)); }
    .status-covered .report-status-badge, .status-covered-candidate .report-status-badge, .status-pass .report-status-badge, .status-not-failed .report-status-badge, .report-status-badge.status-covered, .report-status-badge.status-covered-candidate, .report-status-badge.status-pass, .report-status-badge.status-not-failed { color: var(--stat-add); border-color: color-mix(in srgb, var(--stat-add) 70%, var(--meta-border)); background: color-mix(in srgb, var(--add-bg) 72%, var(--panel)); }
    .status-risk, .status-needs-evidence, .status-not-applicable-candidate, .status-warning, .status-assumption-failure, .status-skip, .status-skipped, .status-auto-warning-candidate { border-color: color-mix(in srgb, var(--comment-border) 70%, var(--meta-border)); }
    .status-risk .report-status-badge, .status-needs-evidence .report-status-badge, .status-not-applicable-candidate .report-status-badge, .status-warning .report-status-badge, .status-assumption-failure .report-status-badge, .status-skip .report-status-badge, .status-skipped .report-status-badge, .status-auto-warning-candidate .report-status-badge, .report-status-badge.status-risk, .report-status-badge.status-needs-evidence, .report-status-badge.status-not-applicable-candidate, .report-status-badge.status-warning, .report-status-badge.status-assumption-failure, .report-status-badge.status-skip, .report-status-badge.status-skipped, .report-status-badge.status-auto-warning-candidate { color: var(--comment-border); border-color: color-mix(in srgb, var(--comment-border) 70%, var(--meta-border)); background: color-mix(in srgb, var(--comment-bg) 70%, var(--panel)); }
    .status-gap, .status-fail, .status-blocked, .status-auto-fail-candidate { border-color: color-mix(in srgb, var(--stat-del) 72%, var(--meta-border)); }
    .status-gap .report-status-badge, .status-fail .report-status-badge, .status-blocked .report-status-badge, .status-auto-fail-candidate .report-status-badge, .report-status-badge.status-gap, .report-status-badge.status-fail, .report-status-badge.status-blocked, .report-status-badge.status-auto-fail-candidate { color: var(--stat-del); border-color: color-mix(in srgb, var(--stat-del) 72%, var(--meta-border)); background: color-mix(in srgb, var(--del-bg) 70%, var(--panel)); }
    .status-auto-pass-candidate { border-color: color-mix(in srgb, var(--graph-status-auto-pass-border) 70%, var(--meta-border)); }
    .status-auto-pass-candidate .report-status-badge, .report-status-badge.status-auto-pass-candidate { color: var(--graph-status-auto-pass-border); border-color: color-mix(in srgb, var(--graph-status-auto-pass-border) 70%, var(--meta-border)); background: color-mix(in srgb, var(--graph-status-auto-pass-bg) 70%, var(--panel)); }
    .status-not-started, .status-not-run, .status-not-done, .status-other, .status-unknown { border-color: color-mix(in srgb, var(--graph-status-neutral-border) 70%, var(--meta-border)); }
    .status-not-started .report-status-badge, .status-not-run .report-status-badge, .status-not-done .report-status-badge, .status-other .report-status-badge, .status-unknown .report-status-badge, .status-auto-no-result-candidate .report-status-badge, .report-status-badge.status-not-started, .report-status-badge.status-not-run, .report-status-badge.status-not-done, .report-status-badge.status-other, .report-status-badge.status-unknown, .report-status-badge.status-auto-no-result-candidate { color: var(--graph-status-neutral-border); border-color: color-mix(in srgb, var(--graph-status-neutral-border) 70%, var(--meta-border)); background: color-mix(in srgb, var(--graph-status-neutral-bg) 70%, var(--panel)); }
    .report-heatmap-grid { display: grid; gap: 6px; overflow-x: auto; padding-bottom: 2px; }
    .report-heatmap-row { display: grid; grid-template-columns: repeat(var(--report-heatmap-columns, 7), minmax(120px, 1fr)); gap: 6px; min-width: max-content; }
    .report-heatmap-row[data-relationship-open-focus] { cursor: pointer; }
    .report-heatmap-row[data-relationship-open-focus]:hover > div { border-color: var(--link); background: var(--button-hover-bg); }
    .report-heatmap-row > div { min-width: 0; padding: 9px 10px; border: 1px solid var(--meta-border); border-radius: 6px; background: var(--meta-panel); overflow-wrap: anywhere; }
    .report-heatmap-header > div { background: var(--header-bg); color: var(--meta-label); font-size: .82em; font-weight: 800; text-transform: uppercase; letter-spacing: .04em; }
    .report-heatmap-cell.status-covered, .report-heatmap-cell.status-covered-candidate { background: color-mix(in srgb, var(--add-bg) 78%, var(--panel)); color: var(--stat-add); font-weight: 800; }
    .report-heatmap-cell.status-risk, .report-heatmap-cell.status-needs-evidence, .report-heatmap-cell.status-not-applicable-candidate, .report-heatmap-cell.status-warning, .report-heatmap-cell.status-assumption-failure, .report-heatmap-cell.status-skip, .report-heatmap-cell.status-skipped, .report-heatmap-cell.status-auto-warning-candidate { background: color-mix(in srgb, var(--comment-bg) 76%, var(--panel)); color: var(--comment-border); font-weight: 800; }
    .report-heatmap-cell.status-gap, .report-heatmap-cell.status-fail, .report-heatmap-cell.status-blocked, .report-heatmap-cell.status-auto-fail-candidate { background: color-mix(in srgb, var(--del-bg) 76%, var(--panel)); color: var(--stat-del); font-weight: 800; }
    .report-heatmap-cell.status-auto-pass-candidate { background: color-mix(in srgb, var(--graph-status-auto-pass-bg) 76%, var(--panel)); color: var(--graph-status-auto-pass-border); font-weight: 800; }
    .report-heatmap-cell.status-not-run, .report-heatmap-cell.status-not-done, .report-heatmap-cell.status-not-started, .report-heatmap-cell.status-other, .report-heatmap-cell.status-unknown, .report-heatmap-cell.status-auto-no-result-candidate { background: color-mix(in srgb, var(--graph-status-neutral-bg) 76%, var(--panel)); color: var(--graph-status-neutral-border); font-weight: 800; }
    .report-metric-table-note { margin: 0 0 10px; color: var(--muted); }
    .report-status-cards-note { margin: 0 0 10px; color: var(--muted); }
    .report-metric-table { width: 100%; min-width: 640px; border-collapse: separate; border-spacing: 0; table-layout: auto; }
    .report-metric-table th, .report-metric-table td { padding: 7px 9px; border-bottom: 1px solid var(--border); border-right: 1px solid var(--border); text-align: left; vertical-align: top; overflow-wrap: anywhere; }
    .report-metric-table th:last-child, .report-metric-table td:last-child { border-right: 0; }
    .report-metric-table tr:last-child th, .report-metric-table tr:last-child td { border-bottom: 0; }
    .report-metric-table thead th { position: sticky; top: 0; z-index: 5; background: var(--header-bg); background-clip: padding-box; color: var(--meta-label); font-size: .82em; text-transform: uppercase; letter-spacing: .04em; white-space: normal; overflow-wrap: break-word; vertical-align: bottom; }
    .report-metric-table-sublabel { display: block; margin-top: 3px; color: var(--muted); font-size: .92em; font-weight: 700; letter-spacing: .02em; text-transform: none; }
    .report-metric-table tbody th { font-weight: 800; white-space: nowrap; }
    .report-metric-table tbody td { font: 700 13px/1.2 ui-monospace, SFMono-Regular, Consolas, monospace; white-space: nowrap; }
    .report-metric-table tbody th.status-covered, .report-metric-table tbody th.status-covered-candidate, .report-metric-table tbody td.status-covered, .report-metric-table tbody td.status-covered-candidate, .report-metric-table tbody td.status-pass, .report-metric-table tbody td.status-not-failed { background: color-mix(in srgb, var(--add-bg) 70%, var(--panel)); color: var(--stat-add); }
    .report-metric-table tbody td.status-risk, .report-metric-table tbody td.status-needs-evidence, .report-metric-table tbody td.status-warning { background: color-mix(in srgb, var(--comment-bg) 70%, var(--panel)); color: var(--comment-border); }
    .report-metric-table tbody td.status-gap, .report-metric-table tbody td.status-fail, .report-metric-table tbody td.status-blocked { background: color-mix(in srgb, var(--del-bg) 70%, var(--panel)); color: var(--stat-del); }
    .report-metric-table tbody td.status-auto-fail-candidate, .report-metric-table tbody td.status-auto-warning-candidate { background: color-mix(in srgb, var(--graph-status-info-bg) 70%, var(--panel)); color: var(--graph-status-info-border); }
    .report-metric-table tbody td.status-auto-pass-candidate { background: color-mix(in srgb, var(--graph-status-auto-pass-bg) 70%, var(--panel)); color: var(--graph-status-auto-pass-border); }
    .report-metric-table tbody td.status-not-run, .report-metric-table tbody td.status-not-done, .report-metric-table tbody td.status-not-started, .report-metric-table tbody td.status-unknown, .report-metric-table tbody td.status-auto-no-result-candidate { background: color-mix(in srgb, var(--graph-status-neutral-bg) 70%, var(--panel)); color: var(--graph-status-neutral-border); }
    .report-metric-cell-link { padding: 0; border: 0; background: none; color: inherit; font: inherit; text-align: left; text-decoration: underline dotted; text-underline-offset: 3px; cursor: pointer; }
    .report-metric-cell-link:hover, .report-metric-cell-link:focus-visible { color: var(--link); text-decoration-style: solid; }
    .report-metric-cell-note { display: block; color: var(--muted); font: 400 12px/1.3 inherit; }
    .report-metric-table-wrap { max-width: 100%; overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; }
    .report-metric-cell-parts { display: inline-flex; flex-wrap: nowrap; gap: 5px; align-items: baseline; }
    .report-metric-cell-part-sep { color: var(--muted); font-weight: 600; }
    .report-metric-cell-part.status-pass, .report-metric-cell-part.status-covered, .report-metric-cell-part.status-covered-candidate, .report-metric-cell-part.status-not-failed { color: var(--stat-add); }
    .report-metric-cell-part.status-fail, .report-metric-cell-part.status-gap, .report-metric-cell-part.status-risk { color: var(--stat-del); }
    .report-metric-cell-part.status-not-run, .report-metric-cell-part.status-not-done, .report-metric-cell-part.status-unknown, .report-metric-cell-part.status-needs-evidence { color: var(--muted); }
    .report-table-filter { display: grid; gap: 5px; max-width: 460px; margin-bottom: 10px; }
    .report-table-filter input { min-height: 36px; padding: 0 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); font: inherit; }
    .report-table-wrap { max-width: 100%; overflow-x: auto; overflow-y: visible; border: 1px solid var(--border); border-radius: 8px; }
    .report-table { width: 100%; min-width: 720px; border-collapse: separate; border-spacing: 0; table-layout: auto; }
    .report-table th, .report-table td { padding: 9px 10px; border-bottom: 1px solid var(--border); border-right: 1px solid var(--border); text-align: left; vertical-align: top; overflow-wrap: anywhere; }
    .report-table th:last-child, .report-table td:last-child { border-right: 0; }
    .report-table tr:last-child td { border-bottom: 0; }
    .report-table thead { position: sticky; top: 0; z-index: 5; }
    .report-table th { position: sticky; top: 0; z-index: 5; background: var(--header-bg); background-clip: padding-box; color: var(--meta-label); font-size: .82em; text-transform: uppercase; letter-spacing: .04em; box-shadow: 0 1px 0 var(--border), 0 6px 12px color-mix(in srgb, var(--shadow) 38%, transparent); }
    .report-table td .report-status-badge { margin-right: 6px; margin-bottom: 4px; }
    .report-timeline-list { position: relative; display: grid; gap: 10px; margin: 0; padding: 0; list-style: none; }
    .report-timeline-list li { display: grid; grid-template-columns: 20px minmax(0, 1fr); gap: 10px; min-width: 0; }
    .report-timeline-marker { width: 14px; height: 14px; margin-top: 6px; border: 3px solid var(--meta-border); border-radius: 999px; background: var(--panel); }
    .report-timeline-content { min-width: 0; padding: 10px 12px; border: 1px solid var(--meta-border); border-radius: 8px; background: var(--meta-panel); overflow-wrap: anywhere; }
    .report-timeline-content time { display: block; color: var(--muted); font: 700 13px/1.3 ui-monospace, SFMono-Regular, Consolas, monospace; }
    .report-timeline-content strong { display: inline-block; margin-right: 8px; }
    .report-timeline-content p { margin: 7px 0 0; white-space: pre-line; }
    .report-artifact-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 10px; }
    .report-artifact { display: grid; gap: 3px; padding: 11px 12px; }
    .report-artifact span { font-weight: 800; overflow-wrap: anywhere; }
    .report-artifact small { color: var(--muted); overflow-wrap: anywhere; }
    body.relationship-modal-open { overflow: hidden; }
    .relationship-launcher { display: flex; gap: 14px; align-items: center; justify-content: flex-start; min-width: 0; padding: 14px 16px; border: 1px solid var(--border); border-radius: 8px; background: var(--meta-panel); }
    .relationship-launcher strong { display: block; margin-bottom: 4px; font-size: 1.02em; overflow-wrap: anywhere; }
    .relationship-launcher p { margin: 0; color: var(--meta-text); overflow-wrap: anywhere; }
    .relationship-preview { display: grid; gap: 7px; margin-top: 12px; }
    .relationship-preview-row { display: flex; flex-wrap: wrap; gap: 6px; }
    .relationship-launcher .relationship-preview-row span, .relationship-launcher .relationship-preview-row button { display: inline-flex; align-items: center; gap: 5px; width: auto; min-width: 0; min-height: 24px; height: auto; padding: 0 8px; border: 1px solid var(--border); border-radius: 999px; background: var(--panel); color: var(--meta-text); box-shadow: none; font: 700 .86em/1.1 var(--font-stack); text-transform: none; letter-spacing: 0; white-space: nowrap; }
    .relationship-preview-row button { cursor: pointer; }
    .relationship-launcher .relationship-preview-row button:hover { border-color: var(--link); background: var(--button-hover-bg); color: var(--link); box-shadow: none; }
    .relationship-preview-row strong { display: inline; margin: 0; font-size: inherit; color: var(--text); }
    .relationship-preview-row span.status-risk, .relationship-preview-row button.status-risk, .relationship-preview-row span.status-needs-evidence, .relationship-preview-row button.status-needs-evidence, .relationship-preview-row span.status-warning, .relationship-preview-row button.status-warning { border-color: color-mix(in srgb, var(--comment-border) 72%, var(--border)); }
    .relationship-preview-row span.status-gap, .relationship-preview-row button.status-gap, .relationship-preview-row span.status-fail, .relationship-preview-row button.status-fail { border-color: color-mix(in srgb, var(--stat-del) 72%, var(--border)); }
    .relationship-preview-row span.status-covered, .relationship-preview-row button.status-covered, .relationship-preview-row span.status-covered-candidate, .relationship-preview-row button.status-covered-candidate, .relationship-preview-row span.status-pass, .relationship-preview-row button.status-pass, .relationship-preview-row span.status-not-failed, .relationship-preview-row button.status-not-failed { border-color: color-mix(in srgb, var(--stat-add) 72%, var(--border)); }
    .relationship-preview-row span.status-assumption-failure, .relationship-preview-row button.status-assumption-failure, .relationship-preview-row span.status-skip, .relationship-preview-row button.status-skip, .relationship-preview-row span.status-skipped, .relationship-preview-row button.status-skipped, .relationship-preview-row span.status-auto-fail-candidate, .relationship-preview-row button.status-auto-fail-candidate, .relationship-preview-row span.status-auto-warning-candidate, .relationship-preview-row button.status-auto-warning-candidate { border-color: color-mix(in srgb, var(--graph-status-info-border) 72%, var(--border)); }
    .relationship-preview-row span.status-auto-pass-candidate, .relationship-preview-row button.status-auto-pass-candidate { border-color: color-mix(in srgb, var(--graph-status-auto-pass-border) 72%, var(--border)); }
    .relationship-preview-row span.status-not-run, .relationship-preview-row button.status-not-run, .relationship-preview-row span.status-not-done, .relationship-preview-row button.status-not-done, .relationship-preview-row span.status-unknown, .relationship-preview-row button.status-unknown, .relationship-preview-row span.status-auto-no-result-candidate, .relationship-preview-row button.status-auto-no-result-candidate { border-color: color-mix(in srgb, var(--graph-status-neutral-border) 72%, var(--border)); }
    .relationship-launcher button, .relationship-modal-head button { min-height: 36px; padding: 0 12px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); font: 800 .92em/1 var(--font-stack); cursor: pointer; white-space: nowrap; }
    .relationship-launcher button { min-height: 44px; padding: 0 18px; border-color: color-mix(in srgb, var(--link) 72%, var(--border)); background: var(--link); color: #fff; box-shadow: 0 0 0 1px color-mix(in srgb, var(--link) 28%, transparent), 0 10px 28px color-mix(in srgb, var(--link) 26%, transparent); }
    .relationship-launcher button:hover { border-color: color-mix(in srgb, var(--link) 82%, #fff); background: color-mix(in srgb, var(--link) 84%, #fff); color: #fff; }
    .relationship-modal-head button:hover { border-color: var(--link); background: var(--button-hover-bg); color: var(--link); }
    .relationship-modal[hidden] { display: none; }
    .relationship-modal { position: fixed; inset: 0; z-index: 2000; display: block; padding: 12px; background: color-mix(in srgb, #000 68%, transparent); overflow: hidden; overscroll-behavior: contain; }
    .relationship-modal-panel { display: grid; grid-template-rows: auto minmax(0, 1fr); gap: 8px; min-width: 0; width: 100%; height: calc(100vh - 24px); min-height: 0; padding: 10px; border: 1px solid var(--border); border-radius: 10px; background: var(--panel); box-shadow: 0 20px 70px color-mix(in srgb, #000 54%, transparent); }
    .relationship-modal-head { display: flex; gap: 12px; align-items: center; justify-content: space-between; min-width: 0; }
    .relationship-modal-head h3 { margin: 0; color: var(--text); font: 850 1.15em/1.2 var(--font-stack); overflow-wrap: anywhere; }
    .relationship-browser { display: grid; grid-template-rows: auto minmax(0, 1fr); gap: 8px; min-width: 0; min-height: 0; }
    .relationship-toolbar { display: grid; grid-template-columns: minmax(0, 1fr); grid-template-areas: "search" "status" "types"; gap: 6px 10px; align-items: end; }
    .relationship-search-controls { grid-area: search; display: grid; grid-template-columns: auto minmax(240px, 1fr); grid-template-areas: "find-label find-label" "regex find-input" "results results"; column-gap: 8px; row-gap: 4px; align-items: center; }
    .relationship-search-controls > * { min-width: 0; }
    .relationship-cell-find-label { grid-area: find-label; }
    .relationship-cell-regex { grid-area: regex; }
    .relationship-cell-find-input { grid-area: find-input; }
    .relationship-search-results { grid-area: results; display: grid; gap: 3px; max-height: min(320px, 38vh); padding: 5px; overflow: auto; border: 1px solid var(--border); border-radius: 8px; background: var(--card-bg); box-shadow: var(--shadow); }
    .relationship-search-results[hidden] { display: none; }
    .relationship-search-result { display: flex; align-items: center; gap: 6px; min-height: 28px; padding: 4px 8px; border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--text); font: 750 12px/1.2 var(--font-stack); text-align: left; cursor: pointer; overflow: hidden; }
    .relationship-search-result.status-covered, .relationship-search-result.status-covered-candidate, .relationship-search-result.status-pass, .relationship-search-result.status-not-failed { border-color: color-mix(in srgb, var(--stat-add) 76%, var(--meta-border)); background: color-mix(in srgb, var(--add-bg) 86%, var(--panel)); }
    .relationship-search-result.status-risk, .relationship-search-result.status-needs-evidence, .relationship-search-result.status-not-applicable-candidate, .relationship-search-result.status-warning { border-color: color-mix(in srgb, var(--comment-border) 76%, var(--meta-border)); background: color-mix(in srgb, var(--comment-bg) 84%, var(--panel)); }
    .relationship-search-result.status-gap, .relationship-search-result.status-fail, .relationship-search-result.status-blocked { border-color: color-mix(in srgb, var(--stat-del) 78%, var(--meta-border)); background: color-mix(in srgb, var(--del-bg) 84%, var(--panel)); }
    .relationship-search-result.status-assumption-failure, .relationship-search-result.status-skip, .relationship-search-result.status-skipped, .relationship-search-result.status-auto-fail-candidate, .relationship-search-result.status-auto-warning-candidate { border-color: color-mix(in srgb, var(--graph-status-info-border) 76%, var(--meta-border)); background: color-mix(in srgb, var(--graph-status-info-bg) 88%, var(--panel)); }
    .relationship-search-result.status-auto-pass-candidate { border-color: color-mix(in srgb, var(--graph-status-auto-pass-border) 76%, var(--meta-border)); background: color-mix(in srgb, var(--graph-status-auto-pass-bg) 88%, var(--panel)); }
    .relationship-search-result.status-not-started, .relationship-search-result.status-not-run, .relationship-search-result.status-not-done, .relationship-search-result.status-unknown, .relationship-search-result.status-auto-no-result-candidate { border-color: color-mix(in srgb, var(--graph-status-neutral-border) 76%, var(--meta-border)); background: color-mix(in srgb, var(--graph-isolated-option-bg) 64%, var(--panel)); }
    .relationship-search-result:hover, .relationship-search-result:focus-visible { border-color: var(--link); background: var(--button-hover-bg); outline: 0; }
    .relationship-search-result.is-selected { border-color: var(--link); box-shadow: inset 0 0 0 1px var(--link), 0 0 0 1px color-mix(in srgb, var(--link) 24%, transparent); }
    .relationship-search-status { flex: 0 0 auto; max-width: 190px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .relationship-search-result-text { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .relationship-search-result mark { padding: 0 2px; border-radius: 3px; background: color-mix(in srgb, #ffd84d 68%, transparent); color: inherit; }
    .relationship-search-message { padding: 6px 8px; color: var(--meta-text); font: 750 12px/1.3 var(--font-stack); }
    .relationship-search-message.is-error { color: var(--status-fail-text); }
    .relationship-toolbar .relationship-search-controls > label.label { display: block; }
    .relationship-view-controls { grid-area: types; display: flex; flex-wrap: wrap; gap: 6px; align-items: flex-start; min-width: 0; }
    .relationship-toolbar label { display: grid; gap: 3px; min-width: 0; }
    .relationship-toolbar .label small { margin-left: 6px; color: var(--muted); font: 700 .92em/1 var(--font-stack); text-transform: none; letter-spacing: 0; }
    .relationship-toolbar input, .relationship-toolbar select { min-height: 32px; min-width: 0; padding: 0 9px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); font: inherit; }
    .relationship-toolbar select option.relationship-option-isolated { color: var(--graph-isolated-option-text); background: var(--graph-isolated-option-bg); }
    .relationship-projection-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; min-width: 0; margin: 0; padding: 2px 0; border: 0; border-radius: 0; background: transparent; }
    .relationship-control-label { color: var(--meta-label); font: 800 11px/1 ui-monospace, SFMono-Regular, Consolas, monospace; text-transform: uppercase; letter-spacing: .04em; white-space: nowrap; }
    .relationship-projection-levels { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; min-width: 0; }
    .relationship-projection-level { position: relative; display: inline-grid; grid-template-columns: auto minmax(96px, auto); align-items: center; gap: 4px; min-height: 26px; color: var(--meta-label); font: 800 11px/1.1 ui-monospace, SFMono-Regular, Consolas, monospace; text-transform: uppercase; letter-spacing: .03em; white-space: nowrap; }
    .relationship-projection-summary { position: relative; min-height: 26px; max-width: 210px; padding: 0 26px 0 9px; border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--text); font: 750 12px/1.1 var(--font-stack); text-align: left; text-transform: none; letter-spacing: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: pointer; }
    .relationship-projection-summary::after { content: "▾"; position: absolute; right: 10px; color: var(--meta-text); }
    .relationship-projection-menu[hidden] { display: none; }
    .relationship-projection-menu { position: absolute; z-index: 60; top: calc(100% + 4px); left: 42px; display: flex; flex-direction: column; gap: 4px; min-width: 190px; max-width: min(320px, calc(100vw - 48px)); max-height: 320px; padding: 8px; overflow: auto; border: 1px solid var(--border); border-radius: 10px; background: var(--card-bg); box-shadow: var(--shadow); text-transform: none; letter-spacing: 0; }
    .relationship-projection-menu label { display: inline-flex; align-items: center; gap: 6px; min-height: 24px; padding: 2px 8px; border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--text); font: 750 12px/1.1 var(--font-stack); white-space: nowrap; cursor: pointer; }
    .relationship-projection-menu input { width: 14px; height: 14px; min-height: 0; margin: 0; padding: 0; accent-color: var(--link); }
    .relationship-projection-menu label.is-disabled { border-color: color-mix(in srgb, var(--border) 64%, transparent); background: color-mix(in srgb, var(--button-bg) 58%, var(--panel)); color: var(--muted); cursor: not-allowed; opacity: .62; }
    .relationship-projection-menu label.is-disabled input { filter: grayscale(1); opacity: .5; }
    .relationship-projection-menu label.is-disabled span { color: var(--muted); }
    .relationship-projection-menu input:disabled + span { color: var(--muted); }
    .relationship-toolbar label.relationship-secondary-toggle { display: inline-flex; align-items: center; justify-content: center; gap: 5px; width: auto; min-width: 0; min-height: 26px; padding: 0 8px; border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--meta-text); font: 750 12px/1.1 var(--font-stack); white-space: nowrap; }
    .relationship-toolbar label.relationship-secondary-toggle input { width: 14px; height: 14px; min-height: 0; margin: 0; padding: 0; accent-color: var(--link); }
    .relationship-toolbar label.relationship-secondary-toggle[hidden] { display: none; }
    .relationship-search-tools { position: relative; display: inline-flex; align-items: center; gap: 6px; width: fit-content; }
    .relationship-search-help-button { display: inline-grid; place-items: center; width: 32px; height: 32px; padding: 0; border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--meta-text); font: 850 13px/1 var(--font-stack); cursor: pointer; }
    .relationship-search-help-button:hover, .relationship-search-help-button[aria-expanded="true"] { border-color: var(--link); background: var(--button-hover-bg); color: var(--link); }
    .relationship-search-help { position: absolute; z-index: 8; left: 0; top: calc(100% + 6px); width: min(360px, calc(100vw - 32px)); padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--panel); color: var(--meta-text); box-shadow: var(--shadow); font: 650 12px/1.35 var(--font-stack); }
    .relationship-search-help[hidden] { display: none; }
    .relationship-search-help strong { display: block; margin-bottom: 6px; color: var(--text); font-weight: 850; }
    .relationship-search-help p { margin: 5px 0 0; }
    .relationship-toolbar label.relationship-search-regex { display: inline-flex; align-items: center; justify-content: center; gap: 5px; width: fit-content; min-height: 32px; padding: 0 10px; border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--meta-text); font: 750 12px/1.1 var(--font-stack); white-space: nowrap; cursor: pointer; }
    .relationship-toolbar label.relationship-search-regex:hover { color: var(--link); }
    .relationship-toolbar label.relationship-search-regex input { width: 13px; height: 13px; min-height: 0; margin: 0; padding: 0; accent-color: var(--link); }
    .relationship-status-filter { grid-area: status; display: flex; flex-wrap: wrap; align-items: center; gap: 5px; min-width: 0; padding: 2px 0; border: 0; border-radius: 0; background: transparent; }
    .relationship-status-filter .relationship-status-chip { display: inline-flex; align-items: center; gap: 5px; min-height: 22px; padding: 1px 7px; font-size: 11px; cursor: pointer; }
    .relationship-status-filter .relationship-status-chip small { color: inherit; font: 800 10px/1 ui-monospace, SFMono-Regular, Consolas, monospace; opacity: .8; }
    .relationship-status-filter label.relationship-status-all, .relationship-status-filter label.relationship-plain-list { display: inline-flex; align-items: center; gap: 4px; min-height: 22px; padding: 1px 9px 1px 7px; border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--meta-text); font: 800 11px/1.1 var(--font-stack); white-space: nowrap; cursor: pointer; }
    .relationship-status-filter label.relationship-status-all:hover, .relationship-status-filter label.relationship-plain-list:hover { border-color: var(--link); color: var(--link); }
    .relationship-status-filter label.relationship-status-all input, .relationship-status-filter label.relationship-plain-list input { width: 13px; height: 13px; min-height: 0; margin: 0; padding: 0; accent-color: var(--link); }
    .relationship-status-filter .relationship-status-chip:hover { border-color: var(--link); }
    .relationship-status-filter .relationship-status-chip.is-off { border-style: dashed; background: color-mix(in srgb, var(--button-bg) 78%, var(--panel)); color: var(--muted); text-decoration: line-through; }
    .relationship-page-controls { display: inline-flex; align-items: center; gap: 5px; min-height: 26px; padding: 0 5px; border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--meta-text); font: 750 12px/1.1 var(--font-stack); white-space: nowrap; }
    .relationship-page-controls button { min-width: 24px; min-height: 22px; padding: 0 6px; }
    .relationship-page-controls span { min-width: 240px; text-align: center; }
    .relationship-page-controls.is-single-page { color: var(--muted); }
    .relationship-control-bar { position: sticky; top: 0; z-index: 4; display: grid; grid-template-columns: minmax(220px, 1fr) auto minmax(220px, 1fr); gap: 8px; align-items: center; min-width: 0; padding: 4px 6px; border: 1px solid var(--border); border-radius: 8px; background: var(--panel); box-shadow: 0 4px 10px color-mix(in srgb, var(--shadow) 26%, transparent); }
    .relationship-filters { flex-basis: 100%; min-width: 0; }
    .relationship-filters > summary { display: inline-flex; align-items: center; gap: 6px; width: fit-content; min-height: 26px; padding: 0 10px; border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--meta-text); font: 800 12px/1.1 var(--font-stack); cursor: pointer; list-style: none; }
    .relationship-filters > summary::-webkit-details-marker { display: none; }
    .relationship-filters > summary::after { content: "\u25be"; color: var(--muted); }
    .relationship-filters[open] > summary::after { content: "\u25b4"; }
    .relationship-filters > summary:hover { border-color: var(--link); color: var(--link); }
    .relationship-filters.is-active > summary { border-color: color-mix(in srgb, var(--link) 62%, var(--border)); background: color-mix(in srgb, var(--button-hover-bg) 64%, var(--meta-panel)); color: var(--link); }
    .relationship-filters-body { padding-top: 6px; }
    .relationship-subfilter-popover { flex-basis: 100%; display: grid; gap: 6px; max-width: min(780px, 100%); margin-top: 2px; padding: 7px 8px; border: 1px solid var(--border); border-radius: 7px; background: color-mix(in srgb, var(--panel) 88%, var(--meta-panel)); box-shadow: none; }
    .relationship-subfilter-section { display: grid; gap: 5px; min-width: 0; }
    .relationship-subfilter-section + .relationship-subfilter-section { padding-top: 6px; border-top: 1px solid color-mix(in srgb, var(--border) 62%, transparent); }
    .relationship-subfilter-head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px; }
    .relationship-subfilter-head strong { color: var(--text); font: 850 12px/1.1 var(--font-stack); }
    .relationship-subfilter-head span { display: inline-flex; flex-wrap: wrap; gap: 6px; }
    .relationship-subfilter-popover fieldset { display: flex; flex-wrap: wrap; gap: 5px; min-width: 0; margin: 0; padding: 6px; border: 1px solid var(--border); border-radius: 7px; }
    .relationship-subfilter-popover legend { padding: 0 5px; color: var(--meta-label); font: 800 11px/1 ui-monospace, SFMono-Regular, Consolas, monospace; text-transform: uppercase; letter-spacing: .04em; }
    .relationship-subfilter-popover label { display: inline-flex; align-items: center; gap: 4px; min-height: 24px; padding: 0 7px; border: 1px solid color-mix(in srgb, var(--border) 70%, transparent); border-radius: 999px; background: var(--meta-panel); color: var(--meta-text); font: 750 12px/1.1 var(--font-stack); white-space: nowrap; }
    .relationship-subfilter-popover input { width: 14px; height: 14px; min-height: 0; margin: 0; padding: 0; accent-color: var(--link); }
    .relationship-subfilter-popover label.relationship-subfilter-all { border-color: color-mix(in srgb, var(--link) 54%, var(--border)); background: color-mix(in srgb, var(--button-hover-bg) 54%, var(--panel)); color: var(--text); font-weight: 850; }
    .relationship-subfilter-popover .status-pass { color: var(--stat-add); font-weight: 800; }
    .relationship-subfilter-popover .status-warning, .relationship-subfilter-popover .status-risk, .relationship-subfilter-popover .status-needs-evidence { color: var(--comment-border); font-weight: 800; }
    .relationship-subfilter-popover .status-fail, .relationship-subfilter-popover .status-gap, .relationship-subfilter-popover .status-blocked { color: var(--stat-del); font-weight: 800; }
    .relationship-subfilter-popover .status-assumption-failure, .relationship-subfilter-popover .status-skip, .relationship-subfilter-popover .status-skipped { color: var(--graph-status-info-border); font-weight: 800; }
    .relationship-subfilter-popover .status-not-run, .relationship-subfilter-popover .status-not-done, .relationship-subfilter-popover .status-unknown { color: var(--graph-status-neutral-border); font-weight: 800; }
    .relationship-subfilter-popover p { margin: 0; color: var(--meta-text); }
    .relationship-nav-controls { grid-column: 1; justify-self: start; display: flex; flex-wrap: nowrap; gap: 6px; align-items: center; }
    .relationship-page-controls { grid-column: 3; justify-self: end; }
    .relationship-toolbar button { min-height: 28px; padding: 0 9px; border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--text); font: 750 .86em/1.1 var(--font-stack); cursor: pointer; }
    .relationship-toolbar button:hover, .relationship-toolbar button.is-active { border-color: var(--link); background: var(--button-hover-bg); color: var(--link); }
    .relationship-toolbar button:disabled { cursor: default; color: var(--muted); border-color: var(--border); background: var(--button-bg); }
    .relationship-layout { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(360px, .8fr); gap: 12px; align-items: start; min-width: 0; }
    .relationship-canvas-wrap, .relationship-detail { min-width: 0; height: min(760px, calc(100vh - 180px)); min-height: 560px; max-height: 760px; border: 1px solid var(--border); border-radius: 8px; background: var(--meta-panel); }
    .relationship-browser.is-graph-ready .relationship-canvas-wrap { border-color: color-mix(in srgb, var(--meta-border) 72%, var(--border)); }
    .relationship-browser.is-graph-active .relationship-toolbar, .relationship-browser.is-graph-active .relationship-control-bar, .relationship-browser.is-graph-active .relationship-selection-panel, .relationship-browser.is-graph-active .relationship-detail { border-color: color-mix(in srgb, var(--link) 36%, var(--border)); }
    .relationship-browser.is-graph-active .relationship-canvas-wrap { border-color: color-mix(in srgb, var(--link) 50%, var(--border)); }
    .relationship-browser.is-graph-focused .relationship-canvas-wrap { border-color: color-mix(in srgb, var(--link) 78%, var(--border)); outline: 2px solid color-mix(in srgb, var(--link) 78%, var(--border)); outline-offset: -2px; box-shadow: 0 0 0 3px color-mix(in srgb, var(--link) 18%, transparent); }
    .relationship-focus-badge { grid-column: 2; justify-self: center; display: inline-flex; align-items: center; justify-content: center; min-width: 188px; min-height: 28px; padding: 0 10px; border: 1px solid color-mix(in srgb, var(--link) 62%, var(--border)); border-radius: 999px; background: color-mix(in srgb, var(--button-hover-bg) 72%, var(--panel)); color: var(--link); cursor: pointer; font: 850 12px/1 var(--font-stack); text-transform: uppercase; letter-spacing: .04em; }
    .relationship-focus-badge:hover { border-color: var(--link); background: var(--button-hover-bg); }
    .relationship-focus-badge[hidden] { display: inline-flex !important; visibility: hidden; pointer-events: none; }
    .relationship-modal .relationship-browser { min-height: 0; }
    .relationship-modal .relationship-layout { grid-template-columns: minmax(0, 2fr) minmax(380px, .72fr); align-items: stretch; min-height: 0; height: 100%; overflow: hidden; }
    .relationship-modal .relationship-canvas-wrap { height: max(420px, calc(100% - 48px)); min-height: 420px; max-height: none; }
    .relationship-modal .relationship-explorer-main { grid-template-rows: auto auto auto; height: 100%; overflow: auto; scroll-padding-top: 0; padding-right: 8px; }
    .relationship-modal .relationship-control-bar { position: static; top: auto; z-index: auto; box-shadow: none; }
    .relationship-modal .relationship-selection-panel { min-height: 360px; isolation: isolate; }
    .relationship-modal .relationship-selection-table-head, .relationship-modal .relationship-selection-table thead { position: static; top: auto; z-index: auto; box-shadow: none; }
    .relationship-modal .relationship-detail { position: static; height: 100%; min-height: 0; max-height: none; }
    .relationship-explorer-main { display: grid; grid-template-rows: auto auto auto; gap: 8px; min-width: 0; min-height: 0; max-height: 100%; overflow: auto; overscroll-behavior: contain; padding-right: 8px; }
    .relationship-canvas-wrap { overflow: hidden; position: relative; background: var(--graph-bg); }
    .relationship-control-bar button { min-height: 28px; padding: 0 10px; border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--text); font: 780 .86em/1 var(--font-stack); cursor: pointer; }
    .relationship-control-bar [data-relationship-back], .relationship-control-bar [data-relationship-forward] { min-width: 34px; padding: 0; font-size: 1.05em; }
    .relationship-control-bar button:hover { border-color: var(--link); background: var(--button-hover-bg); color: var(--link); }
    .relationship-control-bar button:disabled { cursor: default; color: var(--muted); border-color: var(--border); background: var(--button-bg); }
    .relationship-canvas { position: relative; display: block; width: 100%; height: 100%; cursor: grab; }
    .relationship-canvas[data-graph-interactive="false"] { cursor: default; }
    .relationship-canvas[data-graph-message]::after { content: attr(data-graph-message); position: absolute; left: 16px; right: 16px; bottom: 14px; z-index: 2; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: color-mix(in srgb, var(--panel) 88%, transparent); color: var(--meta-text); font-size: .9em; pointer-events: none; }
    .relationship-canvas[data-empty-graph="true"]::after { top: 50%; bottom: auto; transform: translateY(-50%); text-align: center; }
    .relationship-canvas[data-graph-hint="filtered"]::after { top: 14px; bottom: auto; border-color: color-mix(in srgb, var(--comment-border) 62%, var(--border)); color: var(--comment-border); text-align: center; }
    .relationship-canvas:active { cursor: grabbing; }
    .relationship-edge { stroke: color-mix(in srgb, var(--muted) 42%, transparent); stroke-width: 1.2; }
    .relationship-node { cursor: pointer; outline: none; }
    .relationship-node rect { fill: var(--panel); stroke: var(--meta-border); stroke-width: 1.4; filter: drop-shadow(0 2px 4px color-mix(in srgb, var(--shadow) 24%, transparent)); }
    .relationship-node:hover rect, .relationship-node:focus rect { stroke: var(--link); stroke-width: 2; }
    .relationship-node.is-selected rect { stroke: var(--link); stroke-width: 3; }
    .relationship-node.status-covered rect, .relationship-node.status-covered-candidate rect, .relationship-node.status-pass rect { stroke: color-mix(in srgb, var(--stat-add) 72%, var(--meta-border)); }
    .relationship-node.status-risk rect, .relationship-node.status-needs-evidence rect, .relationship-node.status-not-applicable-candidate rect { stroke: color-mix(in srgb, var(--comment-border) 72%, var(--meta-border)); }
    .relationship-node.status-gap rect, .relationship-node.status-fail rect, .relationship-node.status-blocked rect { stroke: color-mix(in srgb, var(--stat-del) 76%, var(--meta-border)); }
    .relationship-node-type { fill: var(--meta-label); font: 800 9px/1 ui-monospace, SFMono-Regular, Consolas, monospace; text-anchor: middle; text-transform: uppercase; letter-spacing: .04em; }
    .relationship-node-label { fill: var(--text); font: 760 12px/1.15 var(--font-stack); text-anchor: middle; }
    .relationship-detail { overflow: auto; overscroll-behavior: contain; padding: 14px; }
    .relationship-detail-head { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: space-between; }
    .relationship-node-pill { display: inline-flex; align-items: center; min-height: 24px; padding: 3px 8px; border: 1px solid var(--border); border-radius: 999px; color: var(--meta-label); background: var(--button-bg); font: 800 12px/1 ui-monospace, SFMono-Regular, Consolas, monospace; }
    .relationship-detail h3 { margin: 12px 0 8px; overflow-wrap: anywhere; }
    .relationship-detail p { margin: 0 0 12px; color: var(--meta-text); white-space: pre-line; overflow-wrap: anywhere; }
    .relationship-detail-fields { display: grid; gap: 0; margin: 12px 0; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
    .relationship-detail-fields dt, .relationship-detail-fields dd { margin: 0; padding: 8px 10px; border-bottom: 1px solid var(--border); overflow-wrap: anywhere; }
    .relationship-detail-fields dt { background: var(--header-bg); color: var(--meta-label); font-size: .78em; font-weight: 850; text-transform: uppercase; letter-spacing: .04em; }
    .relationship-detail-fields dd { background: var(--panel); white-space: pre-line; }
    .relationship-detail-fields dd:last-child { border-bottom: 0; }
    .relationship-related { display: grid; gap: 12px; }
    .relationship-related h4 { margin: 0 0 7px; color: var(--meta-label); font-size: .82em; text-transform: uppercase; letter-spacing: .04em; }
    .relationship-related-list { display: grid; gap: 6px; }
    .relationship-related-list button { display: grid; gap: 2px; width: 100%; min-width: 0; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); text-align: left; cursor: pointer; }
    .relationship-related-list button:hover { border-color: var(--link); background: var(--button-hover-bg); }
    .relationship-related-list button.is-outside-view { border-style: dashed; background: color-mix(in srgb, var(--button-bg) 74%, var(--panel)); color: color-mix(in srgb, var(--text) 68%, var(--muted)); opacity: .76; }
    .relationship-related-list button.is-outside-view:hover { opacity: 1; border-color: var(--link); background: var(--button-hover-bg); }
    .relationship-related-list span { font-weight: 780; overflow-wrap: anywhere; }
    .relationship-related-list small { color: var(--muted); overflow-wrap: anywhere; }
    .relationship-failure-stats { display: grid; gap: 10px; margin: 14px 0; }
    .relationship-failure-stats h4, .relationship-failure-stats h5 { margin: 0; color: var(--meta-label); font-size: .82em; text-transform: uppercase; letter-spacing: .04em; }
    .relationship-failure-stats table { width: 100%; border-collapse: collapse; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; font-size: .9em; }
    .relationship-failure-stats th, .relationship-failure-stats td { padding: 7px 9px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; overflow-wrap: anywhere; }
    .relationship-failure-stats th { width: 34%; background: var(--header-bg); color: var(--meta-label); font-weight: 850; text-transform: uppercase; letter-spacing: .04em; }
    .relationship-failure-list { display: grid; gap: 7px; }
    .relationship-failure-list article { display: grid; gap: 4px; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--panel); }
    .relationship-failure-list strong, .relationship-failure-list p, .relationship-failure-list code { overflow-wrap: anywhere; }
    .relationship-failure-list small { color: var(--muted); }
    .relationship-failure-list p { margin: 0; color: var(--meta-text); }
    .relationship-failure-list code { white-space: pre-wrap; color: var(--text); font-size: .86em; }
    .relationship-selection-panel { display: grid; align-content: start; gap: 0; min-width: 0; min-height: 360px; overflow: visible; }
    .relationship-selection-table { align-self: start; min-width: 0; min-height: 0; border: 1px solid var(--border); border-top: 0; border-radius: 0 0 8px 8px; background: var(--meta-panel); overflow: visible; }
    .relationship-selection-table-head { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: flex-start; padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px 8px 0 0; background: var(--meta-panel); color: var(--meta-label); font-size: .8em; font-weight: 850; text-transform: uppercase; letter-spacing: .04em; }
    .relationship-selection-table-head small { color: var(--muted); font: 700 .92em/1 var(--font-stack); text-transform: none; letter-spacing: 0; }
    .relationship-selection-table-scroll { min-height: 0; overflow: visible; overscroll-behavior: auto; }
    .relationship-selection-table table { width: 100%; border-collapse: separate; border-spacing: 0; table-layout: fixed; font-size: .86em; }
    .relationship-selection-table th, .relationship-selection-table td { padding: 9px 8px; border-bottom: 0; text-align: left; vertical-align: top; overflow-wrap: anywhere; line-height: 1.35; }
    .relationship-selection-table th { background: var(--header-bg); color: var(--meta-label); font-size: .78em; text-transform: uppercase; letter-spacing: .04em; }
    .relationship-selection-table thead tr, .relationship-selection-table tbody tr { box-shadow: inset 0 -1px 0 var(--border); }
    .relationship-selection-table tbody tr { cursor: pointer; }
    .relationship-selection-table tbody tr:hover { background: var(--button-hover-bg); }
    .relationship-selection-table tbody tr.is-focus { box-shadow: inset 4px 0 0 var(--link); }
    .relationship-selection-table tbody tr.is-active { background: color-mix(in srgb, var(--comment-bg) 62%, var(--panel)); box-shadow: inset 4px 0 0 var(--comment-border); }
    .relationship-selection-table td:nth-child(1) { width: 86px; color: var(--meta-label); font-weight: 800; }
    .relationship-selection-table td:nth-child(3) { width: 120px; }
    .relationship-selection-table td:nth-child(4) { width: 64px; color: var(--meta-label); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }
    code { background: rgba(175,184,193,.2); border-radius: 4px; padding: 1px 5px; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }
    pre.stat { max-width: 100%; margin: 10px 0 0; padding: 12px; background: var(--code-bg); border-radius: 6px; overflow-x: auto; white-space: pre-wrap; overflow-wrap: anywhere; }
    .label { display: block; color: var(--meta-label); font-size: .72rem; text-transform: uppercase; letter-spacing: .04em; margin-bottom: 3px; }
    .toc a { display: inline-block; margin: 0 8px 8px 0; color: var(--link); text-decoration: none; }
    .toc a:hover { text-decoration: underline; }
    .report-toc { position: fixed; left: var(--page-gutter); top: calc(var(--page-gutter) + var(--brand-height) + 12px); bottom: calc(var(--page-gutter) + var(--story-nav-height)); z-index: 7; width: var(--nav-width); box-sizing: border-box; padding: 12px 10px; overflow: auto; overscroll-behavior: contain; border: 1px solid var(--border); border-radius: 8px; background: var(--panel); box-shadow: 0 8px 22px rgba(31,35,40,.10); }
    .report-toc-head { position: sticky; top: -12px; z-index: 2; margin: -12px -10px 8px; padding: 10px; border-bottom: 1px solid var(--border); background: var(--panel); color: var(--meta-label); font-size: .78em; font-weight: 800; text-transform: uppercase; letter-spacing: .04em; }
    .report-toc ol { display: grid; gap: 3px; margin: 0; padding: 0; list-style: none; }
    .report-toc a { display: block; min-width: 0; padding: 5px 7px; border-radius: 5px; color: var(--link); text-decoration: none; font-size: .9em; font-weight: 700; line-height: 1.2; overflow-wrap: anywhere; border-left: 3px solid transparent; }
    .report-toc a:hover { background: var(--button-hover-bg); }
    .report-toc a.is-current { background: color-mix(in srgb, var(--comment-bg) 68%, var(--button-hover-bg)); color: var(--text); border-left-color: var(--comment-border); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--comment-border) 32%, transparent); }
    .report-toc-tree { display: grid; gap: 8px; }
    .report-toc-group { min-width: 0; border-left: 1px solid color-mix(in srgb, var(--comment-border) 38%, transparent); padding-left: 8px; }
    .report-toc-group summary { margin: 0 0 4px -8px; padding: 4px 6px; border-radius: 5px; color: color-mix(in srgb, var(--text) 74%, var(--muted)); cursor: pointer; font-size: .78em; font-weight: 820; line-height: 1.2; text-transform: uppercase; letter-spacing: .04em; list-style-position: inside; }
    .report-toc-group summary:hover { background: var(--button-hover-bg); color: var(--text); }
    .report-toc-group ol { gap: 2px; padding-left: 5px; }
    .report-toc-group a { font-size: .84em; font-weight: 690; }
    .review-nav { position: fixed; left: var(--page-gutter); top: var(--review-nav-top); bottom: calc(var(--page-gutter) + var(--story-nav-height)); z-index: 8; width: var(--nav-width); margin: 0; padding: 10px 14px 10px 10px; overflow: auto; overscroll-behavior: contain; box-shadow: 0 8px 22px rgba(31,35,40,.10); }
    .review-nav-head { position: sticky; top: -10px; z-index: 2; display: flex; align-items: center; justify-content: flex-start; gap: 8px; margin: -10px -14px 8px -10px; padding: 10px 14px 8px 10px; background: var(--panel); border-bottom: 1px solid var(--border); box-shadow: 0 2px 0 var(--panel); }
    .review-nav h2 { min-width: 0; margin: 0; font-size: .86em; overflow-wrap: anywhere; }
    .review-nav-tree { display: block; }
    .review-nav [hidden] { display: none !important; }
    .review-nav-children { display: block; margin: 0; padding: 0 0 0 12px; list-style: none; border-left: 1px solid color-mix(in srgb, var(--comment-border) 38%, transparent); }
    .review-nav-children .review-nav-children { border-left-color: color-mix(in srgb, var(--comment-border) 38%, transparent); }
    .review-nav-node { min-width: 0; }
    .review-nav-node:not(.is-open) > .review-nav-comments { display: none; }
    .review-nav-file:not(.is-current) > .review-nav-comments { display: none; }
    .review-nav-row { position: relative; display: grid; grid-template-columns: minmax(0, 1fr); align-items: baseline; min-width: 0; margin: 1px 0; padding: 3px 6px 3px 8px; border-radius: 4px; font-weight: 700; line-height: 1.18; }
    .review-nav-row:hover { background: color-mix(in srgb, var(--button-hover-bg) 44%, transparent); }
    .review-nav-dir > .review-nav-row { position: relative; margin: 5px 0 2px 0; padding: 2px 4px 2px 8px; background: color-mix(in srgb, var(--panel) 91%, var(--comment-bg)); color: color-mix(in srgb, var(--text) 62%, var(--muted)); font-size: .78em; font-weight: 760; letter-spacing: 0; text-transform: none; box-shadow: inset 2px 0 0 color-mix(in srgb, var(--comment-border) 38%, transparent), 0 0 0 1px color-mix(in srgb, var(--comment-border) 10%, transparent); }
    .review-nav-dir > .review-nav-row:hover { background: color-mix(in srgb, var(--panel) 86%, var(--comment-bg)); }
    .review-nav-dir > .review-nav-row::before { content: ""; position: absolute; left: -12px; top: 50%; width: 12px; border-top: 1px solid color-mix(in srgb, var(--comment-border) 38%, transparent); transform: translateY(-.5px); }
    .review-nav-tree > .review-nav-dir > .review-nav-row::before { display: none; }
    .review-nav-dir > .review-nav-row .review-nav-label { font-weight: 780; }
    .review-nav-dir > .review-nav-row .review-nav-label::after { content: "/"; margin-left: 2px; color: color-mix(in srgb, var(--muted) 70%, transparent); }
    .review-nav-tree > .review-nav-dir > .review-nav-row { margin-top: 10px; color: color-mix(in srgb, var(--text) 80%, var(--muted)); font-size: .86em; font-weight: 820; }
    .review-nav-dir .review-nav-dir > .review-nav-row { color: color-mix(in srgb, var(--text) 58%, var(--muted)); font-size: .76em; font-weight: 740; }
    .review-nav-dir.is-current-path > .review-nav-row { background: color-mix(in srgb, var(--comment-bg) 16%, var(--panel)); color: color-mix(in srgb, var(--text) 76%, var(--muted)); box-shadow: inset 4px 0 0 var(--comment-border), 0 0 0 1px color-mix(in srgb, var(--comment-border) 24%, transparent); }
    .review-nav-file > .review-nav-row { margin: 2px 0; padding: 4px 7px 4px 9px; background: transparent; cursor: pointer; box-shadow: inset 2px 0 0 color-mix(in srgb, var(--comment-border) 28%, transparent), 0 0 0 1px color-mix(in srgb, var(--comment-border) 8%, transparent); font-size: .88em; font-weight: 400; }
    .review-nav-file > .review-nav-row::before { content: ""; position: absolute; left: -12px; top: 50%; width: 12px; border-top: 1px solid color-mix(in srgb, var(--comment-border) 38%, transparent); transform: translateY(-.5px); }
    .review-nav-file-with-comments > .review-nav-row { box-shadow: inset 2px 0 0 color-mix(in srgb, var(--comment-border) 28%, transparent), 0 0 0 1px color-mix(in srgb, var(--comment-border) 8%, transparent); }
    .review-nav-file-with-comments > .review-nav-row:hover { background: color-mix(in srgb, var(--button-hover-bg) 68%, transparent); box-shadow: inset 2px 0 0 color-mix(in srgb, var(--comment-border) 56%, transparent); }
    .review-nav-file.is-current > .review-nav-row { margin: 3px 0 4px; padding: 6px 7px 6px 10px; background: color-mix(in srgb, var(--comment-bg) 42%, var(--panel)); color: var(--text); box-shadow: inset 4px 0 0 var(--comment-border), 0 0 0 1px color-mix(in srgb, var(--comment-border) 24%, transparent); }
    .review-nav-file > .review-nav-row .review-nav-label { font-weight: 400; }
    .review-nav-file.is-current > .review-nav-row a { color: var(--text); text-decoration: none; font-weight: 400; }
    .review-nav-file.is-current > .review-nav-row .review-nav-label { color: inherit; }
    .review-nav a { color: var(--text); text-decoration: none; }
    .review-nav a:hover { color: var(--text); text-decoration: none; }
    .review-nav-label { min-width: 0; font-weight: 700; white-space: normal; overflow-wrap: anywhere; word-break: normal; hyphens: none; }
    .review-nav-comments { display: block; margin: 3px 0 2px 18px; padding: 0; list-style: none; }
    .review-nav-comments a { display: grid; grid-template-columns: 3.2em minmax(0, 1fr); gap: 6px; align-items: center; padding: 4px 4px; border-radius: 4px; background: transparent; color: color-mix(in srgb, var(--text) 82%, var(--muted)); font-size: .78em; line-height: 1.25; overflow-wrap: anywhere; }
    .review-nav-comments a:hover { background: var(--button-hover-bg); color: var(--text); text-decoration: none; }
    .review-nav-comments a.is-current-comment { background: color-mix(in srgb, var(--comment-bg) 72%, var(--button-hover-bg)); color: var(--text); box-shadow: inset 3px 0 0 var(--comment-border), 0 0 0 1px color-mix(in srgb, var(--comment-border) 34%, transparent); text-decoration: none; }
    .review-nav-comments a.is-current-comment .review-nav-line { color: var(--comment-border); font-weight: 800; }
    .review-nav-line { display: inline-grid; place-items: center; align-self: stretch; min-height: 1.25em; color: var(--muted); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; text-align: center; }
    .review-nav-resizer { position: fixed; left: calc(var(--nav-width) + var(--page-gutter) - 3px); top: var(--review-nav-top); bottom: calc(var(--page-gutter) + var(--story-nav-height)); width: 10px; cursor: ew-resize; z-index: 20; }
    .review-nav-resizer::before { content: ""; position: absolute; inset: 0 3px; border-radius: 99px; background: transparent; }
    .review-nav-resizer:hover::before, body.is-resizing-review-nav .review-nav-resizer::before { background: rgba(9,105,218,.38); }
    body.is-resizing-review-nav { cursor: ew-resize; user-select: none; }
    .story { position: sticky; top: 0; z-index: 12; padding: 10px 12px; margin-bottom: 0; border-bottom: 0; border-bottom-left-radius: 0; border-bottom-right-radius: 0; box-shadow: 0 8px 22px rgba(31,35,40,.08); transition: left .18s ease, right .18s ease, top .18s ease, width .18s ease, max-width .18s ease; }
    body.has-pinned-story .story, body.has-diagram-open .story { position: fixed; left: calc(var(--nav-width) + var(--page-gutter) * 2); right: var(--page-gutter); top: 0; width: auto; max-width: none; max-height: 30vh; overflow: hidden; z-index: 12; }
    body.has-pinned-story .story.has-vocabulary-popover, body.has-diagram-open .story.has-vocabulary-popover { overflow: visible; z-index: 1009; }
    body.is-resizing-review-nav .story { transition: none; }
    body.has-diagram-open .story { transition: none; }
    .story h2 { margin: 0 0 6px; font-size: var(--scaled-code-font); }
    .to-top-button { position: fixed; right: max(8px, calc(var(--floating-content-gutter) - var(--floating-control-size) - var(--floating-control-gap))); bottom: calc(var(--story-nav-height) + var(--floating-bottom-gap) + var(--floating-control-size) + 10px); z-index: 32; display: inline-flex; align-items: center; justify-content: center; width: var(--floating-control-size); height: var(--floating-control-size); border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--link); box-shadow: 0 10px 28px var(--shadow); cursor: pointer; opacity: 0; visibility: hidden; pointer-events: none; transform: translateY(10px) scale(.96); transition: opacity .18s ease, transform .18s ease, visibility 0s linear .18s, border-color .12s ease, box-shadow .12s ease; font-size: 0; }
    .to-top-button::before { content: ""; width: 13px; height: 13px; border-left: 4px solid currentColor; border-top: 4px solid currentColor; transform: translateY(4px) rotate(45deg); border-radius: 2px; }
    .to-top-button:hover { border-color: var(--link); box-shadow: 0 12px 32px rgba(9,105,218,.22); transform: translateY(0) scale(1.03); }
    body.has-left-top .to-top-button { opacity: 1; visibility: visible; pointer-events: auto; transform: translateY(0) scale(1); transition-delay: 0s; }
    body.story-nav-hidden .to-top-button { bottom: calc(var(--story-nav-height) + var(--floating-bottom-gap) + var(--floating-control-size) + 10px + var(--floating-control-size) + 10px); }
    .story-nav-toggle { position: fixed; right: max(8px, calc(var(--floating-content-gutter) - var(--floating-control-size) - var(--floating-control-gap))); bottom: calc(var(--story-nav-height) + var(--floating-bottom-gap) + var(--floating-control-size) + 10px); z-index: 32; display: inline-flex; align-items: center; justify-content: center; width: var(--floating-control-size); height: var(--floating-control-size); border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--link); box-shadow: 0 10px 28px var(--shadow); cursor: pointer; opacity: 0; visibility: hidden; pointer-events: none; transform: translateY(10px) scale(.96); transition: opacity .18s ease, transform .18s ease, visibility 0s linear .18s, border-color .12s ease, box-shadow .12s ease; font-size: 0; }
    .story-nav-toggle::before { content: ""; width: 18px; height: 14px; border: 3px solid currentColor; border-radius: 3px; box-shadow: inset 0 -4px 0 color-mix(in srgb, currentColor 28%, transparent); }
    .story-nav-toggle::after { content: ""; position: absolute; width: 0; height: 0; border-left: 5px solid transparent; border-right: 5px solid transparent; border-bottom: 7px solid currentColor; transform: translateY(-1px); }
    .story-nav-toggle:hover { border-color: var(--link); box-shadow: 0 12px 32px rgba(9,105,218,.22); transform: translateY(0) scale(1.03); }
    body.story-nav-hidden .story-nav-toggle { opacity: 1; visibility: visible; pointer-events: auto; transform: translateY(0) scale(1); transition-delay: 0s; }
    .story-step-strip { display: grid; grid-template-columns: 32px minmax(0, 1fr) 32px; gap: 6px; align-items: stretch; overflow: hidden; }
    .story-page-button { display: inline-flex; align-items: center; justify-content: center; min-width: 0; min-height: 44px; border: 1px solid var(--story-step-border); border-radius: 6px; background: var(--story-step-bg); color: var(--link); font: 800 20px/1 ui-monospace, SFMono-Regular, Consolas, monospace; cursor: pointer; box-shadow: 0 1px 0 rgba(31,35,40,.08); }
    .story-page-button:hover { border-color: var(--story-step-active-border); background: var(--story-step-hover-bg); }
    .story-page-button:disabled, .story-page-button[aria-disabled="true"] { opacity: .45; cursor: default; border-color: var(--border); color: var(--muted); background: var(--button-bg); box-shadow: none; }
    .story-page-button:focus-visible { outline: 2px solid var(--story-step-active-border); outline-offset: 2px; }
    .story-steps { display: grid; grid-template-rows: minmax(56px, 1fr); grid-auto-columns: var(--story-step-column-width, 260px); align-items: stretch; gap: 6px; margin: 0; padding: 0; overflow: hidden; overscroll-behavior-x: contain; scroll-behavior: smooth; list-style: none; }
    .story-steps li { min-width: 0; }
    .story-step { display: grid; grid-template-columns: 34px minmax(0, 1fr); gap: 7px; align-items: center; width: 100%; height: 100%; min-height: 44px; padding: 8px 10px; border: 1px solid var(--story-step-border); border-radius: 6px; background: var(--story-step-bg); color: var(--text); text-align: left; cursor: pointer; font: inherit; box-shadow: 0 1px 0 rgba(31,35,40,.08); transition: background .12s ease, border-color .12s ease, box-shadow .12s ease, transform .12s ease; contain: layout paint; }
    .story-step:hover { border-color: var(--story-step-active-border); background: var(--story-step-hover-bg); box-shadow: 0 0 0 2px rgba(9,105,218,.18); transform: translateY(-1px); }
    .story-step:focus-visible { outline: 2px solid var(--story-step-active-border); outline-offset: 2px; }
    .story-step.is-active { border-color: var(--story-step-active-border); background: var(--story-step-active-bg); box-shadow: inset 4px 0 0 var(--story-step-active-border), 0 0 0 1px color-mix(in srgb, var(--story-step-active-border) 34%, transparent); }
    .story-step.is-open { border-color: var(--comment-border); background: color-mix(in srgb, var(--comment-bg) 86%, var(--story-step-active-bg)); box-shadow: inset 4px 0 0 var(--comment-border), 0 0 0 2px color-mix(in srgb, var(--comment-border) 45%, transparent), 0 8px 20px rgba(202,80,16,.22); }
    .story-step.is-open .story-step-index { color: var(--comment-border); }
    .story-step-index { color: var(--story-step-active-border); font: 800 var(--scaled-code-font)/1.35 ui-monospace, SFMono-Regular, Consolas, monospace; }
    .story-step-text { display: grid; gap: 3px; min-width: 0; }
    .story-step-text strong { display: -webkit-box; overflow: hidden; overflow-wrap: anywhere; -webkit-box-orient: vertical; -webkit-line-clamp: 2; font-size: clamp(13px, var(--scaled-code-font), 16px); line-height: 1.22; }
    .story-details { min-width: 0; max-width: 100%; margin-top: 7px; border: 1px solid var(--border); border-radius: 6px; background: var(--panel-subtle); }
    .story-details-title { padding: 7px 8px; font-size: var(--scaled-code-font); font-weight: 700; }
    .story-details div:not(.story-details-title) { padding: 0 8px 8px; color: var(--muted); font-size: var(--scaled-code-font); line-height: 1.35; white-space: pre-line; overflow-wrap: anywhere; }
    .asset-inventory { width: min(100%, var(--content-width)); max-width: 100%; min-width: 0; margin-right: auto; margin-left: auto; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 16px; }
    .asset-inventory summary { display: flex; align-items: center; gap: 10px; padding: 14px 20px; font-size: 20px; font-weight: 700; line-height: 1.2; cursor: pointer; user-select: none; }
    .asset-inventory summary:hover { color: var(--link); background: var(--button-hover-bg); }
    .asset-inventory summary:focus-visible { outline: 2px solid var(--link); outline-offset: 2px; }
    .asset-inventory summary::before { content: ">"; color: var(--link); font: 800 var(--scaled-code-font)/1 ui-monospace, SFMono-Regular, Consolas, monospace; }
    .asset-inventory[open] summary { border-bottom: 1px solid var(--border); }
    .asset-inventory[open] summary::before { content: "v"; }
    .asset-inventory .diagram-list { padding: 14px 20px 20px; }
    .story-target-active { outline: 3px solid rgba(9,105,218,.35); outline-offset: 2px; scroll-margin-top: calc(var(--story-offset) + 72px); }
    .story-target-flash { animation: story-target-flash .4s ease-out; }
    .code-target-flash-overlay { position: absolute; z-index: 5; pointer-events: none; border: 3px solid rgba(9,105,218,.92); border-radius: 6px; box-shadow: 0 0 0 2px rgba(9,105,218,.22); animation: code-target-overlay-flash .46s ease-out; }
    .file, .file-comment, .review-comment, tr[id] { scroll-margin-top: calc(var(--story-offset) + 72px); }
    .file-header { margin: -1px -1px 0; padding: 10px 13px; border-bottom: 1px solid var(--border); background: var(--header-bg); font-weight: 700; position: sticky; top: calc(var(--story-offset) - 2px); z-index: 6; box-shadow: 0 1px 0 var(--border); }
    .file-comment { min-width: 0; max-width: calc(100% - 24px); margin: 6px 12px 6px; padding: 8px 12px; border-left: 4px solid var(--comment-border); background: var(--comment-bg); border-radius: 6px; overflow-wrap: anywhere; }
    table.diff { width: 100%; border-collapse: collapse; table-layout: fixed; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: var(--scaled-code-font); line-height: 1.5; }
    .diff td { vertical-align: top; border: 0; padding: 0; }
    .num { width: var(--diff-num-width); padding: 0 10px !important; color: var(--muted); text-align: right; user-select: none; border-right: 1px solid var(--border) !important; }
    .code { white-space: pre-wrap; overflow-wrap: anywhere; padding: 0 10px !important; }
    tr.add .num, tr.add .code { background: var(--add-bg); }
    tr.del .num, tr.del .code { background: var(--del-bg); }
    tr.ctx .num, tr.ctx .code { background: var(--row-bg); }
    tr.hunk .num, tr.hunk .code { background: var(--hunk-bg); color: var(--hunk-text); }
    tr.header .num, tr.header .code { background: var(--header-bg); color: var(--muted); font-weight: 700; }
    tr.comment-target .num, tr.comment-target .code { background: linear-gradient(to right, var(--comment-target-overlay), var(--comment-target-overlay)), var(--comment-target-ctx-bg); border-left: 0; }
    tr.comment-target.add .num, tr.comment-target.add .code { background: linear-gradient(to right, var(--comment-target-overlay), var(--comment-target-overlay)), var(--comment-target-add-bg); }
    tr.comment-target.del .num, tr.comment-target.del .code { background: linear-gradient(to right, var(--comment-target-overlay), var(--comment-target-overlay)), var(--comment-target-del-bg); }
    tr.comment-target .num:first-child { box-shadow: inset 4px 0 0 var(--comment-border); }
    tr.comment-target-start .num, tr.comment-target-start .code { box-shadow: inset 0 2px 0 var(--comment-border); }
    tr.comment-target-end .num, tr.comment-target-end .code { box-shadow: inset 0 -2px 0 var(--comment-border); }
    tr.comment-target-end:has(+ tr.comment-row) .num, tr.comment-target-end:has(+ tr.comment-row) .code { box-shadow: none; }
    tr.comment-target-start .num:first-child { box-shadow: inset 4px 0 0 var(--comment-border), inset 0 2px 0 var(--comment-border); }
    tr.comment-target-end .num:first-child { box-shadow: inset 4px 0 0 var(--comment-border), inset 0 -2px 0 var(--comment-border); }
    tr.comment-target-end:has(+ tr.comment-row) .num:first-child { box-shadow: inset 4px 0 0 var(--comment-border); }
    tr.comment-target-single .num:first-child { box-shadow: inset 4px 0 0 var(--comment-border), inset 0 2px 0 var(--comment-border), inset 0 -2px 0 var(--comment-border); }
    tr.comment-row { --comment-row-target-bg: var(--comment-target-ctx-bg); }
    tr.comment-row-add { --comment-row-target-bg: var(--comment-target-add-bg); }
    tr.comment-row-del { --comment-row-target-bg: var(--comment-target-del-bg); }
    tr.comment-row td { background: linear-gradient(to right, transparent calc(var(--diff-num-width) - 1px), var(--border) calc(var(--diff-num-width) - 1px) var(--diff-num-width), transparent var(--diff-num-width)), linear-gradient(to right, transparent calc(var(--comment-gutter-width) - 1px), var(--border) calc(var(--comment-gutter-width) - 1px) var(--comment-gutter-width), transparent var(--comment-gutter-width)), linear-gradient(to right, var(--comment-target-overlay) 0 var(--comment-gutter-width), transparent var(--comment-gutter-width)), linear-gradient(to right, var(--comment-row-target-bg) 0 var(--comment-gutter-width), transparent var(--comment-gutter-width)); padding: 0 !important; box-shadow: inset 4px 0 0 var(--comment-border); }
    .review-comment { position: relative; margin: 6px 18px 14px 112px; border: 1px solid var(--comment-panel-border); border-left-width: 4px; background: var(--comment-bg); border-radius: 6px; box-shadow: 0 1px 2px rgba(31,35,40,.08); overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    .review-comment .title { padding: 8px 10px; font-weight: 700; border-bottom: 1px solid var(--comment-title-border); background: var(--comment-title-bg); }
    .review-comment .body { min-width: 0; max-width: 100%; padding: 9px 10px; overflow-wrap: anywhere; }
    .diagram-list { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: flex-start; gap: 12px; }
    .diagram-preview-wrap { margin-top: 10px; }
    .diagram-preview { display: block; width: min(420px, 100%); border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); padding: 0; text-align: left; cursor: zoom-in; overflow: hidden; color: inherit; }
    .diagram-preview:hover { border-color: var(--link); box-shadow: 0 0 0 2px rgba(9,105,218,.12); }
    .diagram-preview-title { display: block; padding: 7px 9px; border-bottom: 1px solid var(--border); background: var(--header-bg); font-weight: 700; }
    .diagram-preview-canvas { display: flex; align-items: center; justify-content: center; height: 180px; padding: 10px; overflow: hidden; background: var(--diagram-bg); }
    .diagram-preview-canvas img { display: block; max-width: 100%; max-height: 100%; width: auto; height: auto; }
    .diagram-preview-img-dark { display: none !important; }
    :root[data-theme="dark"] .diagram-preview-img-light { display: none !important; }
    :root[data-theme="dark"] .diagram-preview-img-dark { display: block !important; }
    .diagram-preview-canvas svg { max-width: 100%; max-height: 100%; width: auto; height: auto; filter: var(--diagram-svg-filter); }
    .log-preview { cursor: pointer; }
    .log-preview-text { max-width: 100%; height: 180px; margin: 0; padding: 10px; overflow: hidden; background: #0d1117; color: #e6edf3; font: 18px/1.45 ui-monospace, SFMono-Regular, Consolas, monospace; white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word; text-align: left; }
    .diagram-modal[hidden] { display: none; }
    .diagram-modal { position: fixed; inset: 0; z-index: 10; }
    .diagram-backdrop { position: absolute; inset: 0; background: rgba(31,35,40,.55); }
    .diagram-dialog { position: absolute; left: clamp(28px, 5vw, 92px); right: clamp(28px, 5vw, 92px); top: calc(min(var(--story-offset, 0px), 24vh) + 10px); bottom: calc(var(--story-nav-height) + clamp(8px, 2vh, 24px)); display: flex; flex-direction: column; min-width: 0; min-height: 0; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; box-shadow: 0 16px 48px rgba(31,35,40,.28); }
    .diagram-toolbar { display: grid; grid-template-columns: minmax(180px, 1fr) minmax(0, auto); align-items: center; gap: 10px 12px; padding: 10px 12px; border-bottom: 1px solid var(--border); background: var(--header-bg); }
    .diagram-toolbar h2 { min-width: 0; margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 16px; }
    .diagram-tools { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 6px 8px; min-width: 0; }
    .diagram-search-tools, .diagram-action-tools { display: inline-flex; align-items: center; gap: 6px; min-width: 0; }
    .diagram-search-tools { flex: 1 1 360px; justify-content: flex-end; }
    .diagram-action-tools { flex: 0 0 auto; justify-content: flex-end; }
    .diagram-tools input { width: clamp(160px, 24vw, 260px); height: 32px; border: 1px solid var(--border); border-radius: 6px; padding: 0 9px; font: inherit; }
    .diagram-search-count { min-width: 54px; color: var(--muted); font-size: 13px; text-align: center; }
    .diagram-tools button { display: inline-flex; align-items: center; justify-content: center; min-width: 36px; height: 32px; padding: 0 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); cursor: pointer; font: inherit; line-height: 1; }
    .diagram-tools button:hover { border-color: var(--link); color: var(--link); }
    .diagram-scroll { position: relative; flex: 1; min-height: 0; overflow: auto; padding: 18px; background: var(--diagram-bg); }
    .asset-story-comment { position: fixed; left: 18px; top: 18px; z-index: 11; width: min(520px, calc(100% - 36px)); margin: 0; padding: 10px 12px 10px 48px; border: 1px solid var(--comment-panel-border); border-left: 4px solid var(--comment-border); border-radius: 6px; background: var(--comment-bg); color: var(--text); box-shadow: 0 8px 22px var(--shadow); opacity: 0; visibility: hidden; pointer-events: none; user-select: text; }
    .asset-story-comment.is-positioned { opacity: 1; visibility: visible; pointer-events: auto; }
    .asset-story-comment.is-collapsed { width: 46px !important; height: 46px; padding: 0; border-left-width: 1px; border-color: var(--comment-border); border-radius: 999px; background: transparent; box-shadow: none; overflow: hidden; }
    .asset-story-comment-toggle { position: absolute; left: 5px; top: 5px; display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; padding: 0; border: 2px solid var(--comment-border); border-radius: 999px; background: var(--comment-bg); color: var(--link); cursor: pointer; font: 900 24px/1 ui-monospace, SFMono-Regular, Consolas, monospace; box-shadow: 0 2px 8px var(--shadow); user-select: none; }
    .asset-story-comment-toggle:hover { background: var(--button-hover-bg); color: var(--link); border-color: var(--link); }
    .asset-story-comment-content { min-width: 0; }
    .asset-story-comment.is-collapsed .asset-story-comment-content { display: none; }
    .asset-story-comment strong { display: block; margin-bottom: 4px; }
    .asset-story-comment-body { color: var(--text); font-size: clamp(17px, calc(var(--scaled-code-font) * 1.12), 21px); line-height: 1.48; white-space: pre-line; overflow-wrap: anywhere; }
    .diagram-story-nav { position: fixed; left: 0; right: 0; bottom: 0; z-index: 1004; display: grid; grid-template-columns: minmax(0, 240px) 58px minmax(0, 240px); justify-content: center; gap: 14px; width: auto; min-height: var(--story-nav-height); padding: 12px max(78px, calc(env(safe-area-inset-right) + 78px)) calc(12px + env(safe-area-inset-bottom)) max(16px, env(safe-area-inset-left)); border: 0; border-top: 1px solid var(--story-step-active-border); border-radius: 0; background: color-mix(in srgb, var(--panel) 90%, var(--story-step-active-bg)); box-shadow: 0 -16px 36px rgba(1, 4, 9, .42), 0 -1px 0 color-mix(in srgb, var(--story-step-active-border) 34%, transparent); transition: opacity .18s ease, transform .18s ease, visibility 0s; }
    body.story-nav-hidden .diagram-story-nav { opacity: 0; visibility: hidden; pointer-events: none; transform: translateY(calc(100% + env(safe-area-inset-bottom))); transition: opacity .18s ease, transform .18s ease, visibility 0s; }
    .diagram-story-nav button { display: inline-flex; align-items: center; justify-content: center; width: 100%; min-width: 0; height: 50px; padding: 0 18px; overflow: hidden; border: 1px solid var(--story-step-active-border); border-radius: 6px; background: var(--story-step-active-bg); color: var(--text); cursor: pointer; font: 800 clamp(18px, var(--scaled-body-font), 22px)/1.08 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; white-space: nowrap; text-overflow: ellipsis; box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--story-step-active-border) 22%, transparent); }
    .diagram-story-nav button:hover { border-color: var(--link); color: var(--link); background: var(--button-hover-bg); }
    .diagram-story-nav .story-slide-toggle { position: relative; justify-self: center; width: 50px; padding: 0; overflow: visible; border-radius: 999px; background: radial-gradient(circle at 35% 28%, color-mix(in srgb, var(--button-hover-bg) 74%, white) 0 22%, transparent 23%), linear-gradient(145deg, color-mix(in srgb, var(--story-step-active-bg) 86%, white), color-mix(in srgb, var(--button-bg) 62%, var(--story-step-active-bg))); color: var(--story-step-active-border); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--story-step-active-border) 26%, transparent), 0 8px 20px rgba(9,105,218,.24); }
    .diagram-story-nav .story-slide-toggle::before { content: ""; width: 0; height: 0; margin-left: 3px; border-top: 9px solid transparent; border-bottom: 9px solid transparent; border-left: 14px solid currentColor; filter: drop-shadow(0 1px 0 rgba(0,0,0,.18)); }
    .diagram-story-nav .story-slide-toggle::after { content: attr(data-tooltip); position: absolute; left: 50%; bottom: calc(100% + 10px); z-index: 1005; min-width: max-content; max-width: 180px; padding: 7px 10px; border: 1px solid var(--comment-panel-border); border-radius: 6px; background: var(--comment-bg); color: var(--text); box-shadow: 0 8px 22px var(--shadow); font: 800 14px/1.2 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; opacity: 0; pointer-events: none; transform: translate(-50%, 6px); transition: opacity .14s ease, transform .14s ease; }
    .diagram-story-nav .story-slide-toggle:hover::after, .diagram-story-nav .story-slide-toggle:focus-visible::after { opacity: 1; transform: translate(-50%, 0); }
    .diagram-story-nav .story-slide-toggle:hover { border-color: var(--story-step-active-border); background: radial-gradient(circle at 35% 28%, color-mix(in srgb, var(--button-hover-bg) 78%, white) 0 22%, transparent 23%), linear-gradient(145deg, color-mix(in srgb, var(--story-step-active-bg) 72%, white), var(--story-step-active-bg)); color: var(--story-step-active-border); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--story-step-active-border) 34%, transparent), 0 10px 24px rgba(9,105,218,.32); }
    .diagram-story-nav .story-slide-toggle.is-open { border-color: var(--stat-del); background: radial-gradient(circle at 35% 28%, color-mix(in srgb, var(--del-bg) 55%, white) 0 22%, transparent 23%), linear-gradient(145deg, color-mix(in srgb, var(--del-bg) 74%, var(--button-bg)), color-mix(in srgb, var(--button-bg) 60%, var(--stat-del))); color: var(--stat-del); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--stat-del) 30%, transparent), 0 8px 20px color-mix(in srgb, var(--stat-del) 24%, transparent); }
    .diagram-story-nav .story-slide-toggle.is-open::before { width: 18px; height: 18px; margin-left: 0; border: 0; background: linear-gradient(45deg, transparent calc(50% - 2px), currentColor calc(50% - 2px) calc(50% + 2px), transparent calc(50% + 2px)), linear-gradient(-45deg, transparent calc(50% - 2px), currentColor calc(50% - 2px) calc(50% + 2px), transparent calc(50% + 2px)); filter: drop-shadow(0 1px 0 rgba(0,0,0,.18)); }
    .diagram-story-nav .story-nav-hide { position: absolute; right: max(16px, calc(env(safe-area-inset-right) + 16px)); top: 12px; width: 50px; height: 50px; padding: 0; border-radius: 999px; font-size: 28px; line-height: 1; transform: none; box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--story-step-active-border) 18%, transparent); }
    .diagram-story-nav button:disabled, .diagram-story-nav button[aria-disabled="true"] { opacity: .48; cursor: default; border-color: var(--border); color: var(--muted); background: var(--button-bg); box-shadow: none; }
    .diagram-code-overlay { position: fixed; inset: 0; z-index: 1002; background: var(--overlay-bg); box-sizing: border-box; }
    .diagram-code-popover { position: fixed; left: 50vw; top: 50vh; transform: translate(-50%, -50%); width: min(1120px, calc(100vw - 32px)); height: min(86vh, calc(100vh - 32px)); margin: 0; border: 1px solid var(--border); border-radius: 8px; background: var(--panel); box-shadow: 0 12px 32px var(--shadow); overflow: hidden; display: flex; flex-direction: column; }
    .diagram-code-overlay[hidden] { display: none; }
    .diagram-code-popover-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 12px; border-bottom: 1px solid var(--border); background: var(--header-bg); }
    .diagram-code-popover-title { display: grid; gap: 2px; min-width: 0; color: var(--text); font-weight: 800; }
    .diagram-code-popover-file { color: var(--diagram-code-file); font: 20px/1.35 ui-monospace, SFMono-Regular, Consolas, monospace; overflow-wrap: anywhere; }
    .diagram-code-popover-close { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; padding: 0; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); cursor: pointer; font: inherit; line-height: 1; }
    .diagram-code-popover-close:hover { border-color: var(--link); color: var(--link); }
    .diagram-code-popover-body { flex: 1; min-height: 0; padding: 10px 12px; overflow: auto; }
    .diagram-code-link-item { display: block; margin: 0 0 10px; padding: 9px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: inherit; }
    .diagram-code-link-title { display: block; font-weight: 700; margin-bottom: 4px; }
    .diagram-code-link-location { display: block; color: var(--muted); font: 13px/1.35 ui-monospace, SFMono-Regular, Consolas, monospace; margin-bottom: 6px; }
    .diagram-code-link-code { display: block; max-height: none; overflow: visible; padding: 8px; border-radius: 4px; background: var(--code-bg); font: var(--scaled-code-font)/1.45 ui-monospace, SFMono-Regular, Consolas, monospace; white-space: pre-wrap; overflow-wrap: anywhere; }
    .diagram-code-line { display: block; min-width: 0; padding: 0 4px; white-space: pre-wrap; overflow-wrap: anywhere; }
    .diagram-code-context-line { background: var(--diagram-code-context-bg); }
    .diagram-code-target-line { background: var(--diagram-code-target-bg); border-left: 3px solid var(--diagram-code-target-border); padding-left: 1px; font-weight: 700; }
    .diagram-scroll[data-mode="diagram"] .diagram-zoom-stage { cursor: grab; }
    .diagram-scroll.is-panning, .diagram-scroll.is-panning .diagram-zoom-stage { cursor: grabbing; user-select: none; }
    .diagram-zoom-stage { transform-origin: 0 0; width: max-content; min-width: 100%; }
    .diagram-scroll[data-mode="log"] .diagram-zoom-stage { width: 100%; max-width: 100%; min-width: 0; }
    .diagram-scroll.is-preparing-story-view .diagram-zoom-stage { visibility: hidden; }
    .diagram-zoom-stage svg { display: block; max-width: none; height: auto; filter: var(--diagram-svg-filter); }
    .diagram-zoom-stage svg text, .diagram-zoom-stage svg tspan { cursor: text; user-select: text; }
""" + plantuml_svg_styles() + """
    .log-view-text { width: 100%; max-width: 100%; min-width: 0; margin: 0; color: #e6edf3; background: #0d1117; padding: 14px; border-radius: 6px; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: calc(20px * var(--asset-log-scale, 1)); line-height: 1.45; white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word; transition: font-size .16s ease; }
    .log-view-text * { max-width: 100%; white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word; }
    .asset-focus-line { display: block; min-width: 0; margin: 0 -4px; padding: 0 4px; background: rgba(255, 171, 112, .32); border-left: 3px solid #fb8500; }
    mark.asset-search-match { background: #fff8c5; color: inherit; padding: 0 1px; border-radius: 2px; }
    mark.asset-search-current { background: #ffab70; outline: 1px solid #fb8500; }
    @keyframes story-target-flash { 0% { box-shadow: 0 0 0 0 rgba(9,105,218,.75), inset 0 0 0 3px rgba(9,105,218,.8); filter: saturate(1.28) brightness(1.03); } 55% { box-shadow: 0 0 0 10px rgba(9,105,218,.22), inset 0 0 0 2px rgba(9,105,218,.5); filter: saturate(1.12) brightness(1.01); } 100% { box-shadow: 0 0 0 16px rgba(9,105,218,0), inset 0 0 0 0 rgba(9,105,218,0); filter: saturate(1) brightness(1); } }
    @keyframes code-target-overlay-flash { 0% { opacity: 1; transform: scale(1.004); box-shadow: 0 0 0 0 rgba(9,105,218,.42), 0 0 0 2px rgba(9,105,218,.32); } 70% { opacity: .96; box-shadow: 0 0 0 8px rgba(9,105,218,.18), 0 0 0 2px rgba(9,105,218,.22); } 100% { opacity: 0; transform: scale(1); box-shadow: 0 0 0 12px rgba(9,105,218,0), 0 0 0 0 rgba(9,105,218,0); } }
    @media (prefers-reduced-motion: reduce) {
      .story-target-flash, .code-target-flash-overlay { animation: none; }
    }
    @media (min-width: 1800px) {
      :root {
        --nav-width: 460px;
        --brand-height: 260px;
        --brand-mark-size: 176px;
        --brand-title-size: 84px;
        --brand-subtitle-size: 42px;
        --content-width: 1500px;
        --screen-body-font: 20px;
        --screen-code-font: 16px;
      }
    }
    @media (max-width: 1500px) {
      :root {
        --nav-width: 350px;
        --brand-height: 188px;
        --brand-top-padding: 12px;
        --brand-mark-size: 128px;
        --brand-title-size: 58px;
        --brand-subtitle-size: 29px;
        --brand-gap: 12px;
        --brand-padding-x: 12px;
        --content-width: 1120px;
        --screen-body-font: 16px;
        --screen-code-font: 14px;
        --diff-num-width: 56px;
        --comment-gutter-width: 96px;
      }
      header, section { padding: 16px; }
      .num { padding: 0 8px !important; }
      .review-comment { margin-left: 96px; }
    }
    @media (max-width: 1280px) {
      :root {
        --nav-width: 300px;
        --brand-height: 174px;
        --brand-mark-size: 134px;
        --brand-title-size: 58px;
        --brand-subtitle-size: 29px;
        --brand-gap: 8px;
        --brand-padding-x: 8px;
        --content-width: 920px;
        --screen-body-font: 15px;
        --screen-code-font: 13px;
      }
      .review-nav { padding-right: 10px; }
      .story-step { grid-template-columns: 28px minmax(0, 1fr); padding: 7px 8px; }
      .report-card-grid { grid-template-columns: 1fr; }
      .report-card-metrics > span { grid-template-columns: 1fr; gap: 4px; }
    }
    @media (max-width: 1440px) and (min-width: 1101px) {
      .relationship-search-controls { grid-template-columns: auto minmax(0, 1fr); grid-template-areas: "find-label find-label" "regex find-input" "results results"; }
    }
    @media (max-width: 1100px) {
      :root {
        --nav-width: 0px;
        --screen-body-font: 16px;
        --screen-code-font: 13px;
        --content-width: 100%;
      }
      body { font-size: var(--scaled-body-font); }
      main { width: calc(100% - 16px); max-width: calc(100vw - 16px); margin: 8px auto calc(16px + var(--story-nav-height)); }
      header, section, .file, .asset-inventory { width: 100%; margin-left: 0; margin-right: 0; }
      .report-brand { display: none; }
      .report-settings-launcher { right: 14px; bottom: calc(var(--story-nav-height) + var(--floating-bottom-gap)); }
      .relationship-launcher, .relationship-modal-head { align-items: stretch; flex-direction: column; }
      .relationship-modal { padding: 10px; overflow: auto; }
      .relationship-modal-panel { height: auto; min-height: calc(100vh - 20px); padding: 10px; }
      .relationship-toolbar, .relationship-view-controls, .relationship-layout { grid-template-columns: 1fr; }
      .relationship-search-controls { grid-template-columns: auto minmax(0, 1fr); grid-template-areas: "find-label find-label" "regex find-input" "focus-label focus-label" "focus-input focus-input" "results results"; }
      .relationship-modal .relationship-layout { grid-template-columns: minmax(0, 1fr); height: auto; overflow: visible; }
      .relationship-explorer-main { max-height: none; overflow: visible; overscroll-behavior: auto; padding-right: 0; }
      .relationship-modal .relationship-detail { position: static; height: auto; min-height: 360px; }
      .relationship-modal .relationship-canvas-wrap { height: 100vh; min-height: 420px; }
      .relationship-modal .relationship-selection-table-head, .relationship-modal .relationship-selection-table thead { position: static; top: auto; z-index: auto; box-shadow: none; }
      .relationship-canvas-wrap, .relationship-canvas, .relationship-canvas canvas, .relationship-selection-panel, .relationship-selection-table, .relationship-selection-table-scroll { touch-action: pan-y; overscroll-behavior: auto; }
      .relationship-selection-panel { min-height: 340px; }
      .relationship-selection-table { min-height: 0; }
      .relationship-control-bar { grid-template-columns: auto minmax(0, 1fr) auto; }
      .relationship-focus-badge { min-width: 0; max-width: 220px; width: 100%; }
      .relationship-nav-controls { flex-wrap: wrap; }
      .to-top-button { right: 14px; bottom: calc(var(--story-nav-height) + var(--floating-bottom-gap) + var(--floating-control-size) + 12px); }
      body.story-nav-hidden .to-top-button { bottom: calc(var(--story-nav-height) + var(--floating-bottom-gap) + var(--floating-control-size) + 12px + var(--floating-control-size) + 12px); }
      .story-nav-toggle { right: 14px; bottom: calc(var(--story-nav-height) + var(--floating-bottom-gap) + var(--floating-control-size) + 12px); }
      .report-toc, .review-nav { position: static; width: calc(100% - 16px); max-height: none; margin: 8px auto 16px; overflow: visible; overscroll-behavior: auto; touch-action: pan-y; }
      .review-nav-resizer { display: none; }
      .story { top: 0; }
      body.has-pinned-story .story, body.has-diagram-open .story { left: 8px; right: 8px; top: 0; max-height: 35vh; }
      .story-step-strip { grid-template-columns: 28px minmax(0, 1fr) 28px; gap: 5px; }
      .story-page-button { min-height: 42px; }
      .diagram-dialog { left: 12px; right: 12px; top: calc(min(var(--story-offset, 0px), 28vh) + 8px); bottom: calc(var(--story-nav-height) + 8px); }
      .diagram-toolbar { grid-template-columns: 1fr; align-items: start; }
      .diagram-tools { justify-content: stretch; }
      .diagram-search-tools { flex: 1 1 100%; justify-content: stretch; }
      .diagram-action-tools { margin-left: auto; }
      .diagram-tools input { flex: 1 1 auto; width: auto; min-width: 0; }
    }
"""

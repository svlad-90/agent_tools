from __future__ import annotations

import html


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
    :root {{
      color-scheme: light;
      --bg: #f3f3f3;
      --panel: #fbfbfc;
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
      --comment-bg: #fff3c4;
      --comment-border: #ca5010;
      --comment-target-bg: #e9f5ec;
      --comment-target-mix: rgba(26,127,55,.16);
      --comment-row-bg: rgba(233,245,236,.86);
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
      --diagram-focus: #1d4ed8;
      --diagram-link: #107c10;
      --diagram-link-bg: #e9f5e9;
      --diagram-link-hover-bg: #deecf9;
      --diagram-svg-filter: none;
      --diagram-svg-text: #111827;
      --diagram-svg-line: #475569;
      --diagram-svg-box-bg: #ffffff;
      --diagram-svg-note-bg: #fff8c5;
      --diagram-note-bg: #dbeafe;
      --diagram-note-hover-bg: #bfdbfe;
      --diagram-note-text: #111827;
      --diagram-note-link: #2563eb;
      --diagram-note-marker-bg: #eff6ff;
      --overlay-bg: rgba(31,35,40,.42);
      --page-gutter: 8px;
      --nav-width: 430px;
      --brand-height: 250px;
      --brand-top-padding: 16px;
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
      --text-scale: 1;
      --screen-body-font: 18px;
      --screen-code-font: 15px;
      --scaled-body-font: calc(var(--screen-body-font) * var(--text-scale));
      --scaled-code-font: calc(var(--screen-code-font) * var(--text-scale));
      --content-width: 1260px;
      --floating-control-size: 44px;
      --floating-control-gap: 18px;
      --floating-content-gutter: max(24px, calc((100vw - var(--nav-width) - var(--content-width)) / 2));
    }}
    :root[data-theme="dark"] {{
      color-scheme: dark;
      --bg: #1e1e1e;
      --panel: #252526;
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
      --comment-bg: #3a3217;
      --comment-border: #cca700;
      --comment-target-bg: #2f2a1d;
      --comment-target-mix: rgba(204,167,0,.22);
      --comment-row-bg: rgba(58,50,23,.62);
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
      --diagram-link: #4ec9b0;
      --diagram-link-bg: #173f3a;
      --diagram-link-hover-bg: #094771;
      --diagram-svg-filter: none;
      --diagram-svg-text: #d4d4d4;
      --diagram-svg-line: #c5c5c5;
      --diagram-svg-box-bg: #252526;
      --diagram-svg-note-bg: #3a3217;
      --diagram-note-bg: #1f2f46;
      --diagram-note-hover-bg: #094771;
      --diagram-note-text: #d4d4d4;
      --diagram-note-link: #3794ff;
      --diagram-note-marker-bg: #173f5f;
      --overlay-bg: rgba(0,0,0,.68);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--bg); color: var(--text); font: var(--scaled-body-font)/1.52 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    main {{ width: calc(100% - var(--nav-width) - (var(--page-gutter) * 3)); max-width: calc(100% - var(--nav-width) - (var(--page-gutter) * 3)); min-width: 0; margin: var(--page-gutter) var(--page-gutter) 16px calc(var(--nav-width) + (var(--page-gutter) * 2)); }}
    .report-brand {{ position: fixed; left: var(--page-gutter); top: var(--page-gutter); z-index: 4; display: flex; align-items: center; justify-content: center; width: var(--nav-width); height: var(--brand-height); padding-top: 0; pointer-events: none; color: var(--brand-text); }}
    .report-brand::before {{ content: ""; position: absolute; inset: 0; height: var(--brand-height); border-radius: 10px; background: var(--brand-panel); box-shadow: 0 10px 24px var(--shadow); }}
    .report-brand-inner {{ position: relative; display: grid; grid-template-columns: var(--brand-mark-size) max-content; align-items: center; justify-content: center; gap: var(--brand-gap); width: auto; max-width: 100%; min-height: 0; padding: 16px var(--brand-padding-x); font-weight: 800; letter-spacing: 0; }}
    .report-brand-mark {{ display: flex; align-items: center; justify-content: center; width: var(--brand-mark-size); height: var(--brand-mark-size); border-radius: 10px; background: #0969da; color: #fff; font: 800 calc(var(--brand-mark-size) * .64)/1 ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .report-brand-text {{ display: grid; gap: 2px; min-width: 0; line-height: 1.05; }}
    .report-brand-title {{ font-size: var(--brand-title-size); white-space: nowrap; }}
    .report-brand-subtitle {{ color: var(--muted); font-size: var(--brand-subtitle-size); white-space: nowrap; }}
    .settings-launcher {{ position: fixed; right: max(8px, calc(var(--floating-content-gutter) - var(--floating-control-size) - var(--floating-control-gap))); bottom: 24px; z-index: 32; width: auto; opacity: 1; visibility: visible; pointer-events: auto; transform: translateY(0) scale(1); transition: opacity .18s ease, transform .18s ease, visibility 0s linear .18s, border-color .12s ease, box-shadow .12s ease; }}
    .settings-toggle {{ display: inline-flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; width: var(--floating-control-size); height: var(--floating-control-size); padding: 0; border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--link); box-shadow: 0 10px 28px var(--shadow); cursor: pointer; font: 800 18px/1 ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .settings-toggle span, .settings-toggle::before, .settings-toggle::after {{ content: ""; display: block; width: 18px; height: 2px; border-radius: 99px; background: currentColor; }}
    .settings-toggle:hover {{ border-color: var(--link); box-shadow: 0 12px 32px rgba(9,105,218,.22); }}
    .settings-modal[hidden] {{ display: none; }}
    .settings-modal {{ position: fixed; inset: 0; z-index: 1100; }}
    .settings-backdrop {{ position: absolute; inset: 0; background: var(--overlay-bg); }}
    .settings-dialog {{ position: absolute; left: 50%; top: 50%; display: grid; gap: 18px; width: min(460px, calc(100vw - 40px)); max-height: calc(100vh - 40px); overflow: auto; transform: translate(-50%, -50%); padding: 20px; border: 1px solid var(--border); border-radius: 8px; background: var(--panel); color: var(--text); box-shadow: 0 18px 58px rgba(0,0,0,.42); font-size: var(--screen-body-font); }}
    .settings-dialog-head {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; }}
    .settings-dialog h2 {{ margin: 0; color: var(--text); font-size: 20px; }}
    .settings-close {{ display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; padding: 0; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); cursor: pointer; font: 22px/1 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .settings-close:hover {{ border-color: var(--link); color: var(--link); }}
    .settings-menu {{ display: grid; gap: 12px; }}
    .settings-group {{ display: grid; gap: 6px; }}
    .settings-label {{ color: var(--meta-label); font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: .04em; }}
    .settings-options {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }}
    .settings-option {{ display: inline-flex; align-items: center; justify-content: center; min-width: 0; height: 34px; padding: 0 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); cursor: pointer; font: 700 15px/1 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .settings-option:hover {{ border-color: var(--link); color: var(--link); }}
    .settings-option.is-active {{ border-color: var(--link); background: var(--settings-active-bg); color: var(--settings-active-text); box-shadow: inset 3px 0 0 var(--link); }}
    .settings-scale-controls {{ display: grid; grid-template-columns: 40px minmax(0, 1fr) 40px; gap: 8px; align-items: center; }}
    .settings-scale-value {{ display: inline-flex; align-items: center; justify-content: center; min-width: 0; height: 34px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); font: 700 14px/1 ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .settings-scale-button {{ display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 34px; padding: 0; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--link); cursor: pointer; font: 800 18px/1 ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .settings-scale-button:hover {{ border-color: var(--link); background: var(--button-hover-bg); }}
    .settings-scale-button:disabled {{ cursor: default; opacity: .45; border-color: var(--border); background: var(--button-bg); color: var(--muted); }}
    .copy-context-menu[hidden] {{ display: none; }}
    .copy-context-menu {{ position: fixed; z-index: 1200; min-width: 178px; padding: 6px; border: 1px solid var(--border); border-radius: 8px; background: var(--panel); box-shadow: 0 12px 32px var(--shadow); }}
    .copy-context-menu button {{ display: flex; align-items: center; justify-content: flex-start; width: 100%; min-height: 32px; padding: 0 10px; border: 0; border-radius: 6px; background: transparent; color: var(--text); cursor: pointer; font: 700 14px/1.2 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; text-align: left; }}
    .copy-context-menu button:hover, .copy-context-menu button:focus-visible {{ background: var(--button-hover-bg); color: var(--link); outline: none; }}
    header, section, .file {{ width: min(100%, var(--content-width)); max-width: 100%; min-width: 0; margin-right: auto; margin-left: auto; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 16px; }}
    .file {{ border-top: 0; }}
    header, section {{ padding: 20px; }}
    h1, h2 {{ margin: 0 0 12px; line-height: 1.2; }}
    h1 {{ font-size: 28px; }}
    h2 {{ font-size: 20px; }}
    p {{ margin: 0 0 10px; }}
    .review-summary-blocks {{ display: grid; gap: 12px; }}
    .review-summary {{ white-space: pre-line; overflow-wrap: anywhere; }}
    .review-summary-blocks .review-summary {{ margin: 0; }}
    .summary-artifact-preview .diagram-preview-wrap {{ margin-top: 0; }}
    .report-note, .review-summary {{ display: block; width: 100%; max-width: 100%; min-width: 0; margin: 0; padding: 12px; border: 1px solid var(--meta-border); border-radius: 6px; background: var(--meta-panel); color: var(--meta-text); white-space: pre-wrap; overflow-wrap: anywhere; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .report-note {{ max-width: 100%; }}
    .diff-stats {{ display: grid; gap: 10px; }}
    .diff-stats-row {{ display: grid; gap: 10px; }}
    .diff-stats-lines {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .diff-stats-files {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
    .diff-stats-row div {{ min-width: 0; max-width: 100%; padding: 12px; border: 1px solid var(--meta-border); border-radius: 6px; background: var(--meta-panel); color: var(--meta-text); overflow-wrap: anywhere; }}
    .diff-stats .label {{ font-size: .86rem; }}
    .diff-stats strong {{ display: block; margin-top: 4px; font: 800 calc(var(--scaled-code-font) * 1.08)/1.2 ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .diff-stat-add {{ color: var(--stat-add); }}
    .diff-stat-del {{ color: var(--stat-del); }}
    code {{ background: rgba(175,184,193,.2); border-radius: 4px; padding: 1px 5px; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }}
    pre.stat {{ max-width: 100%; margin: 10px 0 0; padding: 12px; background: var(--code-bg); border-radius: 6px; overflow-x: auto; white-space: pre-wrap; overflow-wrap: anywhere; }}
    .label {{ display: block; color: var(--meta-label); font-size: .72rem; text-transform: uppercase; letter-spacing: .04em; margin-bottom: 3px; }}
    .toc a {{ display: inline-block; margin: 0 8px 8px 0; color: var(--link); text-decoration: none; }}
    .toc a:hover {{ text-decoration: underline; }}
    .review-nav {{ position: fixed; left: var(--page-gutter); top: var(--review-nav-top); bottom: var(--page-gutter); z-index: 8; width: var(--nav-width); margin: 0; padding: 10px 14px 10px 10px; overflow: auto; box-shadow: 0 8px 22px rgba(31,35,40,.10); }}
    .review-nav-head {{ position: sticky; top: -10px; z-index: 2; display: flex; align-items: center; justify-content: space-between; gap: 8px; margin: -10px -14px 8px -10px; padding: 10px 14px 8px 10px; background: var(--panel); border-bottom: 1px solid var(--border); box-shadow: 0 2px 0 var(--panel); }}
    .review-nav h2 {{ margin: 0; font-size: .86em; }}
    .review-nav-head button {{ display: inline-flex; align-items: center; justify-content: center; min-width: 102px; height: 28px; padding: 0 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); cursor: pointer; font: var(--scaled-code-font)/1 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .review-nav-head button:hover {{ border-color: var(--link); color: var(--link); }}
    .review-nav-tree {{ display: block; }}
    .review-nav [hidden] {{ display: none !important; }}
    .review-nav-children {{ display: block; margin: 0; padding: 0 0 0 14px; list-style: none; border-left: 1px solid rgba(208,215,222,.9); }}
    .review-nav-node {{ min-width: 0; }}
    .review-nav-node:not(.is-open) > .review-nav-children, .review-nav-node:not(.is-open) > .review-nav-comments {{ display: none; }}
    .review-nav-row {{ display: grid; grid-template-columns: 1em minmax(0, 1fr); gap: 2px; align-items: baseline; min-width: 0; padding: 3px 4px; border-radius: 4px; font-weight: 700; line-height: 1.18; }}
    .review-nav-row:hover {{ background: var(--button-hover-bg); }}
    .review-nav-file.is-current > .review-nav-row {{ background: color-mix(in srgb, var(--link) 18%, var(--panel)); box-shadow: inset 4px 0 0 var(--link); }}
    .review-nav-file.is-current > .review-nav-row a {{ color: var(--link); text-decoration: underline; text-decoration-thickness: 1.5px; text-underline-offset: 3px; }}
    .review-nav-file.is-current > .review-nav-row .review-nav-label {{ color: inherit; }}
    .review-nav-toggle {{ display: inline-flex; align-items: center; justify-content: center; width: 1em; height: 1.18em; padding: 0; border: 0; background: transparent; color: var(--muted); cursor: pointer; font: inherit; line-height: 1; }}
    .review-nav-toggle-spacer {{ display: inline-block; width: 1em; }}
    .review-nav-twist::before {{ content: ">"; display: inline-block; width: 1em; color: var(--muted); }}
    .review-nav-node.is-open > .review-nav-row .review-nav-twist::before {{ content: "v"; }}
    .review-nav a {{ color: var(--link); text-decoration: none; }}
    .review-nav a:hover {{ text-decoration: underline; }}
    .review-nav-label {{ min-width: 0; font-weight: 700; white-space: normal; overflow-wrap: anywhere; word-break: normal; hyphens: none; }}
    .review-nav-comments {{ display: block; margin: 3px 0 2px 18px; padding: 0; list-style: none; }}
    .review-nav-comments a {{ display: grid; grid-template-columns: 3.2em minmax(0, 1fr); gap: 6px; align-items: baseline; padding: 4px 4px; border-radius: 4px; font-size: .78em; line-height: 1.25; overflow-wrap: anywhere; }}
    .review-nav-comments a:hover {{ background: var(--button-hover-bg); text-decoration: none; }}
    .review-nav-line {{ color: var(--muted); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .review-nav-resizer {{ position: fixed; left: calc(var(--nav-width) + var(--page-gutter) - 3px); top: var(--review-nav-top); bottom: var(--page-gutter); width: 10px; cursor: ew-resize; z-index: 20; }}
    .review-nav-resizer::before {{ content: ""; position: absolute; inset: 0 3px; border-radius: 99px; background: transparent; }}
    .review-nav-resizer:hover::before, body.is-resizing-review-nav .review-nav-resizer::before {{ background: rgba(9,105,218,.38); }}
    body.is-resizing-review-nav {{ cursor: ew-resize; user-select: none; }}
    .story {{ position: sticky; top: 0; z-index: 12; padding: 10px 12px; margin-bottom: 0; border-bottom: 0; border-bottom-left-radius: 0; border-bottom-right-radius: 0; box-shadow: 0 8px 22px rgba(31,35,40,.08); }}
    .story h2 {{ margin: 0; font-size: var(--scaled-code-font); }}
    .to-top-button {{ position: fixed; right: max(8px, calc(var(--floating-content-gutter) - var(--floating-control-size) - var(--floating-control-gap))); bottom: calc(24px + var(--floating-control-size) + 10px); z-index: 32; display: inline-flex; align-items: center; justify-content: center; width: var(--floating-control-size); height: var(--floating-control-size); border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--link); box-shadow: 0 10px 28px var(--shadow); cursor: pointer; opacity: 0; visibility: hidden; pointer-events: none; transform: translateY(10px) scale(.96); transition: opacity .18s ease, transform .18s ease, visibility 0s linear .18s, border-color .12s ease, box-shadow .12s ease; font-size: 0; }}
    .to-top-button::before {{ content: ""; width: 13px; height: 13px; border-left: 4px solid currentColor; border-top: 4px solid currentColor; transform: translateY(4px) rotate(45deg); border-radius: 2px; }}
    .to-top-button:hover {{ border-color: var(--link); box-shadow: 0 12px 32px rgba(9,105,218,.22); transform: translateY(0) scale(1.03); }}
    body.has-left-top .to-top-button {{ opacity: 1; visibility: visible; pointer-events: auto; transform: translateY(0) scale(1); transition-delay: 0s; }}
    .story-steps {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); align-items: stretch; gap: 6px; margin: 0; padding: 0; list-style: none; }}
    .story-steps li {{ min-width: 0; }}
    .story-step {{ display: grid; grid-template-columns: 34px minmax(0, 1fr); gap: 7px; align-items: center; width: 100%; height: 100%; min-height: 44px; padding: 8px 10px; border: 1px solid var(--story-step-border); border-radius: 6px; background: var(--story-step-bg); color: var(--text); text-align: left; cursor: pointer; font: inherit; box-shadow: 0 1px 0 rgba(31,35,40,.08); transition: background .12s ease, border-color .12s ease, box-shadow .12s ease, transform .12s ease; }}
    .story-step:hover {{ border-color: var(--story-step-active-border); background: var(--story-step-hover-bg); box-shadow: 0 0 0 2px rgba(9,105,218,.18); transform: translateY(-1px); }}
    .story-step:focus-visible {{ outline: 2px solid var(--story-step-active-border); outline-offset: 2px; }}
    .story-step.is-active {{ border-color: var(--story-step-active-border); background: var(--story-step-active-bg); box-shadow: inset 4px 0 0 var(--story-step-active-border), 0 0 0 1px color-mix(in srgb, var(--story-step-active-border) 34%, transparent); }}
    .story-step-index {{ color: var(--story-step-active-border); font: 800 var(--scaled-code-font)/1.35 ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .story-step-text {{ display: grid; gap: 3px; min-width: 0; }}
    .story-step-text strong {{ display: -webkit-box; overflow: hidden; overflow-wrap: anywhere; -webkit-box-orient: vertical; -webkit-line-clamp: 2; font-size: var(--scaled-code-font); line-height: 1.25; }}
    .story-details {{ min-width: 0; max-width: 100%; margin-top: 7px; border: 1px solid var(--border); border-radius: 6px; background: var(--panel-subtle); }}
    .story-details-title {{ padding: 7px 8px; font-size: var(--scaled-code-font); font-weight: 700; }}
    .story-details div:not(.story-details-title) {{ padding: 0 8px 8px; color: var(--muted); font-size: var(--scaled-code-font); line-height: 1.35; white-space: pre-line; overflow-wrap: anywhere; }}
    .asset-inventory {{ width: min(100%, var(--content-width)); max-width: 100%; min-width: 0; margin-right: auto; margin-left: auto; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 16px; }}
    .asset-inventory summary {{ display: flex; align-items: center; gap: 10px; padding: 14px 20px; font-size: 20px; font-weight: 700; line-height: 1.2; cursor: pointer; user-select: none; }}
    .asset-inventory summary:hover {{ color: var(--link); background: var(--button-hover-bg); }}
    .asset-inventory summary:focus-visible {{ outline: 2px solid var(--link); outline-offset: 2px; }}
    .asset-inventory summary::before {{ content: ">"; color: var(--link); font: 800 var(--scaled-code-font)/1 ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .asset-inventory[open] summary {{ border-bottom: 1px solid var(--border); }}
    .asset-inventory[open] summary::before {{ content: "v"; }}
    .asset-inventory .diagram-list {{ padding: 14px 20px 20px; }}
    .story-target-active {{ outline: 3px solid rgba(9,105,218,.35); outline-offset: 2px; scroll-margin-top: calc(var(--story-offset) + 72px); }}
    .story-target-flash {{ animation: story-target-flash .4s ease-out; }}
    .code-target-flash-overlay {{ position: absolute; z-index: 45; pointer-events: none; border: 3px solid rgba(9,105,218,.92); border-radius: 6px; box-shadow: 0 0 0 2px rgba(9,105,218,.22); animation: code-target-overlay-flash .46s ease-out; }}
    .file, .file-comment, .review-comment, tr[id] {{ scroll-margin-top: calc(var(--story-offset) + 72px); }}
    .file-header {{ margin: -1px -1px 0; padding: 10px 13px; border-bottom: 1px solid var(--border); background: var(--header-bg); font-weight: 700; position: sticky; top: calc(var(--story-offset) - 2px); z-index: 6; box-shadow: 0 1px 0 var(--border); }}
    .file-comment {{ min-width: 0; max-width: calc(100% - 24px); margin: 6px 12px 6px; padding: 8px 12px; border-left: 4px solid var(--comment-border); background: var(--comment-bg); border-radius: 6px; overflow-wrap: anywhere; }}
    table.diff {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: var(--scaled-code-font); line-height: 1.5; }}
    .diff td {{ vertical-align: top; border: 0; padding: 0; }}
    .num {{ width: 64px; padding: 0 10px !important; color: var(--muted); text-align: right; user-select: none; border-right: 1px solid var(--border) !important; }}
    .code {{ white-space: pre-wrap; overflow-wrap: anywhere; padding: 0 10px !important; }}
    tr.add .num, tr.add .code {{ background: var(--add-bg); }}
    tr.del .num, tr.del .code {{ background: var(--del-bg); }}
    tr.ctx .num, tr.ctx .code {{ background: var(--row-bg); }}
    tr.hunk .num, tr.hunk .code {{ background: var(--hunk-bg); color: #0969da; }}
    tr.header .num, tr.header .code {{ background: var(--header-bg); color: var(--muted); font-weight: 700; }}
    tr.comment-target .num, tr.comment-target .code {{ background: var(--comment-target-bg); border-left: 0; }}
    tr.comment-target.add .num, tr.comment-target.add .code, tr.comment-target.del .num, tr.comment-target.del .code {{ background: linear-gradient(to right, var(--comment-target-mix), var(--comment-target-mix)), var(--comment-target-bg); }}
    tr.comment-target .num:first-child {{ box-shadow: inset 4px 0 0 var(--comment-border); }}
    tr.comment-target-start .num, tr.comment-target-start .code {{ box-shadow: inset 0 2px 0 var(--comment-border); }}
    tr.comment-target-end .num, tr.comment-target-end .code {{ box-shadow: inset 0 -2px 0 var(--comment-border); }}
    tr.comment-target-start .num:first-child {{ box-shadow: inset 4px 0 0 var(--comment-border), inset 0 2px 0 var(--comment-border); }}
    tr.comment-target-end .num:first-child {{ box-shadow: inset 4px 0 0 var(--comment-border), inset 0 -2px 0 var(--comment-border); }}
    tr.comment-target-single .num:first-child {{ box-shadow: inset 4px 0 0 var(--comment-border), inset 0 2px 0 var(--comment-border), inset 0 -2px 0 var(--comment-border); }}
    tr.comment-row td {{ background: linear-gradient(to right, var(--comment-row-bg) 0 112px, transparent 112px); padding: 0 !important; box-shadow: inset 4px 0 0 var(--comment-border); }}
    .review-comment {{ position: relative; margin: 6px 18px 14px 112px; border: 1px solid var(--comment-panel-border); border-left-width: 4px; background: var(--comment-bg); border-radius: 6px; box-shadow: 0 1px 2px rgba(31,35,40,.08); overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .review-comment::before {{ content: ""; position: absolute; top: -7px; left: -4px; width: 4px; height: 7px; background: var(--comment-border); }}
    .review-comment .title {{ padding: 8px 10px; font-weight: 700; border-bottom: 1px solid var(--comment-title-border); background: var(--comment-title-bg); }}
    .review-comment .body {{ min-width: 0; max-width: 100%; padding: 9px 10px; overflow-wrap: anywhere; }}
    .diagram-list {{ display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: flex-start; gap: 12px; }}
    .diagram-preview-wrap {{ margin-top: 10px; }}
    .diagram-preview {{ display: block; width: min(420px, 100%); border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); padding: 0; text-align: left; cursor: zoom-in; overflow: hidden; color: inherit; }}
    .diagram-preview:hover {{ border-color: var(--link); box-shadow: 0 0 0 2px rgba(9,105,218,.12); }}
    .diagram-preview-title {{ display: block; padding: 7px 9px; border-bottom: 1px solid var(--border); background: var(--header-bg); font-weight: 700; }}
    .diagram-preview-canvas {{ display: flex; align-items: center; justify-content: center; height: 180px; padding: 10px; overflow: hidden; background: var(--diagram-bg); }}
    .diagram-preview-canvas img {{ display: block; max-width: 100%; max-height: 100%; width: auto; height: auto; }}
    .diagram-preview-img-dark {{ display: none !important; }}
    :root[data-theme="dark"] .diagram-preview-img-light {{ display: none !important; }}
    :root[data-theme="dark"] .diagram-preview-img-dark {{ display: block !important; }}
    .diagram-preview-canvas svg {{ max-width: 100%; max-height: 100%; width: auto; height: auto; filter: var(--diagram-svg-filter); }}
    .log-preview {{ cursor: pointer; }}
    .log-preview-text {{ max-width: 100%; height: 180px; margin: 0; padding: 10px; overflow: hidden; background: #0d1117; color: #e6edf3; font: 18px/1.45 ui-monospace, SFMono-Regular, Consolas, monospace; white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word; text-align: left; }}
    .diagram-modal[hidden] {{ display: none; }}
    .diagram-modal {{ position: fixed; inset: 0; z-index: 1000; }}
    .diagram-backdrop {{ position: absolute; inset: 0; background: rgba(31,35,40,.55); }}
    .diagram-dialog {{ position: absolute; inset: max(32px, 5vh) max(32px, 5vw); display: flex; flex-direction: column; min-width: 0; min-height: 0; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; box-shadow: 0 16px 48px rgba(31,35,40,.28); }}
    .diagram-toolbar {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 12px; border-bottom: 1px solid var(--border); background: var(--header-bg); }}
    .diagram-toolbar h2 {{ margin: 0; font-size: 16px; }}
    .diagram-tools {{ display: flex; align-items: center; gap: 6px; }}
    .diagram-tools input {{ width: 220px; height: 32px; border: 1px solid var(--border); border-radius: 6px; padding: 0 9px; font: inherit; }}
    .diagram-search-count {{ min-width: 54px; color: var(--muted); font-size: 13px; text-align: center; }}
    .diagram-tools button {{ display: inline-flex; align-items: center; justify-content: center; min-width: 36px; height: 32px; padding: 0 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); cursor: pointer; font: inherit; line-height: 1; }}
    .diagram-tools button:hover {{ border-color: var(--link); color: var(--link); }}
    .diagram-story-context {{ padding: 9px 12px; border-bottom: 1px solid var(--border); background: var(--button-hover-bg); }}
    .diagram-story-context[hidden] {{ display: none; }}
    .diagram-story-context strong {{ display: block; margin-bottom: 3px; }}
    .diagram-story-context div {{ color: var(--muted); font-size: 13px; white-space: pre-line; overflow-wrap: anywhere; }}
    .diagram-scroll {{ position: relative; flex: 1; min-height: 0; overflow: auto; padding: 18px; background: var(--diagram-bg); }}
    .diagram-code-overlay {{ position: fixed; inset: 0; z-index: 1002; background: var(--overlay-bg); box-sizing: border-box; }}
    .diagram-code-popover {{ position: fixed; left: 50vw; top: 50vh; transform: translate(-50%, -50%); width: min(50vw, calc(100vw - 64px)); height: min(76vh, calc(100vh - 64px)); margin: 0; border: 1px solid var(--border); border-radius: 8px; background: var(--panel); box-shadow: 0 12px 32px var(--shadow); overflow: hidden; display: flex; flex-direction: column; }}
    .diagram-code-overlay[hidden] {{ display: none; }}
    .diagram-code-popover-header {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 12px; border-bottom: 1px solid var(--border); background: var(--header-bg); }}
    .diagram-code-popover-title {{ display: grid; gap: 2px; min-width: 0; color: var(--text); font-weight: 800; }}
    .diagram-code-popover-file {{ color: var(--diagram-code-file); font: 20px/1.35 ui-monospace, SFMono-Regular, Consolas, monospace; overflow-wrap: anywhere; }}
    .diagram-code-popover-close {{ display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; padding: 0; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); cursor: pointer; font: inherit; line-height: 1; }}
    .diagram-code-popover-close:hover {{ border-color: var(--link); color: var(--link); }}
    .diagram-code-popover-body {{ flex: 1; min-height: 0; padding: 10px 12px; overflow: auto; }}
    .diagram-code-link-item {{ display: block; margin: 0 0 10px; padding: 9px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: inherit; }}
    .diagram-code-link-title {{ display: block; font-weight: 700; margin-bottom: 4px; }}
    .diagram-code-link-location {{ display: block; color: var(--muted); font: 13px/1.35 ui-monospace, SFMono-Regular, Consolas, monospace; margin-bottom: 6px; }}
    .diagram-code-link-code {{ display: block; max-height: none; overflow: visible; padding: 8px; border-radius: 4px; background: var(--code-bg); font: var(--scaled-code-font)/1.45 ui-monospace, SFMono-Regular, Consolas, monospace; white-space: pre-wrap; overflow-wrap: anywhere; }}
    .diagram-code-line {{ display: block; min-width: 0; padding: 0 4px; white-space: pre-wrap; overflow-wrap: anywhere; }}
    .diagram-code-context-line {{ background: var(--diagram-code-context-bg); }}
    .diagram-code-target-line {{ background: var(--diagram-code-target-bg); border-left: 3px solid var(--diagram-code-target-border); padding-left: 1px; font-weight: 700; }}
    .diagram-scroll[data-mode="diagram"] .diagram-zoom-stage {{ cursor: grab; }}
    .diagram-scroll.is-panning, .diagram-scroll.is-panning .diagram-zoom-stage {{ cursor: grabbing; user-select: none; }}
    .diagram-zoom-stage {{ transform-origin: 0 0; width: max-content; min-width: 100%; }}
    .diagram-scroll[data-mode="log"] .diagram-zoom-stage {{ width: 100%; max-width: 100%; min-width: 0; }}
    .diagram-zoom-stage svg {{ display: block; max-width: none; height: auto; filter: var(--diagram-svg-filter); }}
    :root[data-theme="dark"] .diagram-preview-canvas svg text:not(.diagram-note-text):not(.diagram-note-marker-text):not(.diagram-code-link-badge-text):not(.asset-focus-match):not(.asset-focus-related-hover),
    :root[data-theme="dark"] .diagram-zoom-stage svg text:not(.diagram-note-text):not(.diagram-note-marker-text):not(.diagram-code-link-badge-text):not(.asset-focus-match):not(.asset-focus-related-hover),
    :root[data-theme="dark"] .diagram-preview-canvas svg tspan:not(.diagram-note-text):not(.diagram-note-marker-text):not(.asset-focus-match):not(.asset-focus-related-hover),
    :root[data-theme="dark"] .diagram-zoom-stage svg tspan:not(.diagram-note-text):not(.diagram-note-marker-text):not(.asset-focus-match):not(.asset-focus-related-hover) {{ fill: var(--diagram-svg-text) !important; }}
    :root[data-theme="dark"] .diagram-preview-canvas svg line:not(.asset-focus-connector):not(.diagram-code-link-connector):not(.diagram-note-link),
    :root[data-theme="dark"] .diagram-zoom-stage svg line:not(.asset-focus-connector):not(.diagram-code-link-connector):not(.diagram-note-link),
    :root[data-theme="dark"] .diagram-preview-canvas svg path:not(.diagram-note-box):not(.diagram-note-link),
    :root[data-theme="dark"] .diagram-zoom-stage svg path:not(.diagram-note-box):not(.diagram-note-link),
    :root[data-theme="dark"] .diagram-preview-canvas svg polyline:not(.asset-focus-connector):not(.diagram-code-link-connector),
    :root[data-theme="dark"] .diagram-zoom-stage svg polyline:not(.asset-focus-connector):not(.diagram-code-link-connector) {{ stroke: var(--diagram-svg-line) !important; }}
    :root[data-theme="dark"] .diagram-preview-canvas svg polygon:not(.asset-focus-connector):not(.diagram-code-link-connector),
    :root[data-theme="dark"] .diagram-zoom-stage svg polygon:not(.asset-focus-connector):not(.diagram-code-link-connector) {{ fill: var(--diagram-svg-line) !important; stroke: var(--diagram-svg-line) !important; }}
    :root[data-theme="dark"] .diagram-preview-canvas svg rect:not(.diagram-note-box):not(.diagram-code-link-badge-box),
    :root[data-theme="dark"] .diagram-zoom-stage svg rect:not(.diagram-note-box):not(.diagram-code-link-badge-box) {{ fill: var(--diagram-svg-box-bg) !important; stroke: var(--diagram-svg-line) !important; }}
    :root[data-theme="dark"] .diagram-preview-canvas svg path[fill="#FBFB77"],
    :root[data-theme="dark"] .diagram-zoom-stage svg path[fill="#FBFB77"] {{ fill: var(--diagram-svg-note-bg) !important; stroke: var(--comment-border) !important; }}
    .log-view-text {{ width: 100%; max-width: 100%; min-width: 0; margin: 0; color: #e6edf3; background: #0d1117; padding: 14px; border-radius: 6px; font: 20px/1.45 ui-monospace, SFMono-Regular, Consolas, monospace; white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word; }}
    .log-view-text * {{ max-width: 100%; white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word; }}
    .asset-focus-line {{ display: block; min-width: 0; margin: 0 -4px; padding: 0 4px; background: rgba(255, 171, 112, .32); border-left: 3px solid #fb8500; }}
    mark.asset-search-match {{ background: #fff8c5; color: inherit; padding: 0 1px; border-radius: 2px; }}
    mark.asset-search-current {{ background: #ffab70; outline: 1px solid #fb8500; }}
    svg .asset-focus-connector {{ stroke: var(--diagram-focus) !important; stroke-width: 3px !important; opacity: .95; filter: drop-shadow(0 0 2px rgba(255,255,255,.95)); }}
    svg line.asset-focus-connector, svg path.asset-focus-connector, svg polyline.asset-focus-connector {{ stroke-dasharray: 10 7; animation: focus-dash-flow 1.1s linear infinite; }}
    svg line.asset-focus-connector-reverse, svg path.asset-focus-connector-reverse, svg polyline.asset-focus-connector-reverse {{ animation-name: focus-dash-flow-reverse; }}
    svg polygon.asset-focus-connector {{ fill: var(--diagram-focus) !important; opacity: .95; filter: drop-shadow(0 0 2px rgba(255,255,255,.95)); animation: focus-arrow-pulse 1.1s ease-in-out infinite; }}
    svg .asset-focus-match {{ fill: var(--diagram-focus) !important; stroke: none !important; }}
    :root[data-theme="dark"] .diagram-preview-canvas svg text.asset-focus-match,
    :root[data-theme="dark"] .diagram-zoom-stage svg text.asset-focus-match,
    :root[data-theme="dark"] .diagram-preview-canvas svg tspan.asset-focus-match,
    :root[data-theme="dark"] .diagram-zoom-stage svg tspan.asset-focus-match {{ fill: var(--diagram-focus) !important; stroke: none !important; }}
    svg .diagram-note-panel {{ opacity: 0; pointer-events: none; transition: opacity .12s ease; }}
    svg .diagram-note-hover .diagram-note-panel, svg .diagram-note-hotspot:hover .diagram-note-panel {{ opacity: 1; pointer-events: auto; }}
    svg .diagram-note-box {{ fill: var(--diagram-note-bg); stroke: var(--diagram-note-link); stroke-width: 1.8px; rx: 6px; ry: 6px; filter: drop-shadow(0 2px 4px rgba(15,23,42,.22)); }}
    svg .diagram-note-text, svg .diagram-note-text tspan {{ fill: var(--diagram-note-text) !important; font: 12px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; pointer-events: none; }}
    svg .diagram-note-link {{ fill: none; stroke: var(--diagram-note-link); stroke-width: 1.8px; opacity: .95; filter: drop-shadow(0 0 2px rgba(255,255,255,.95)); }}
    svg .diagram-note-marker {{ fill: var(--diagram-note-marker-bg); stroke: var(--diagram-note-link); stroke-width: 1.8px; filter: drop-shadow(0 1px 2px rgba(15,23,42,.2)); }}
    svg .diagram-note-marker-text {{ fill: var(--diagram-note-link); font: 700 13px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; text-anchor: middle; dominant-baseline: central; pointer-events: none; }}
    svg .diagram-note-hotspot {{ cursor: pointer; }}
    svg .diagram-note-hover .diagram-note-box, svg .diagram-note-hotspot:hover .diagram-note-box {{ fill: var(--diagram-note-hover-bg); stroke: var(--diagram-note-link); stroke-width: 2.4px; }}
    svg .diagram-note-hover .diagram-note-marker, svg .diagram-note-hotspot:hover .diagram-note-marker {{ fill: var(--diagram-note-hover-bg); stroke: var(--diagram-note-link); stroke-width: 2.4px; }}
    svg .diagram-note-hover .diagram-note-link, svg .diagram-note-hotspot:hover .diagram-note-link {{ stroke: var(--diagram-note-link); stroke-width: 2.1px; opacity: 1; }}
    svg .diagram-note-hover .diagram-note-text, svg .diagram-note-hotspot:hover .diagram-note-text,
    svg .diagram-note-hover .diagram-note-text tspan, svg .diagram-note-hotspot:hover .diagram-note-text tspan {{ fill: var(--diagram-note-text) !important; }}
    svg .diagram-code-link-target {{ fill: var(--diagram-link) !important; text-decoration: underline; text-decoration-thickness: 1.5px; }}
    svg .diagram-code-link-connector {{ stroke: var(--diagram-link) !important; stroke-width: 2.6px !important; opacity: .96; }}
    svg polygon.diagram-code-link-connector {{ fill: var(--diagram-link) !important; }}
    svg .diagram-code-link-badge {{ cursor: pointer; }}
    svg .diagram-code-link-badge rect {{ fill: var(--diagram-link-bg); stroke: var(--diagram-link); stroke-width: 1.4px; rx: 5px; ry: 5px; filter: drop-shadow(0 1px 2px rgba(15,23,42,.18)); }}
    svg .diagram-code-link-badge text {{ fill: var(--diagram-link); font: 700 11px ui-monospace, SFMono-Regular, Consolas, monospace; text-anchor: middle; dominant-baseline: central; pointer-events: none; }}
    svg .diagram-code-link-badge.diagram-code-link-hover rect {{ fill: var(--diagram-link-hover-bg); stroke: var(--diagram-focus); }}
    svg .diagram-code-link-badge.diagram-code-link-hover text {{ fill: var(--diagram-focus); }}
    svg .diagram-code-link-active {{ filter: drop-shadow(0 0 3px rgba(4,120,87,.65)); }}
    svg .asset-focus-connector.diagram-code-link-connector {{ stroke: var(--diagram-focus) !important; stroke-width: 3px !important; opacity: .95; }}
    svg polygon.asset-focus-connector.diagram-code-link-connector {{ fill: var(--diagram-focus) !important; }}
    svg text.asset-focus-match.diagram-code-link-target, svg tspan.asset-focus-match.diagram-code-link-target {{ fill: var(--diagram-focus) !important; stroke: none !important; }}
    svg .asset-focus-related-hover {{ stroke: var(--diagram-focus) !important; fill: var(--diagram-focus) !important; opacity: 1 !important; filter: drop-shadow(0 0 2px rgba(255,255,255,.95)); }}
    svg text.asset-focus-related-hover, svg tspan.asset-focus-related-hover {{ fill: var(--diagram-focus) !important; stroke: none !important; }}
    svg .asset-search-match {{ fill: #cf222e !important; stroke: none !important; }}
    svg .asset-search-submatch {{ fill: transparent; stroke: #ff4d5e; stroke-width: 2px; vector-effect: non-scaling-stroke; opacity: .98; }}
    svg .asset-search-current {{ fill: #ff2a3d !important; stroke: none !important; filter: none; font-weight: 800 !important; text-decoration: underline; text-decoration-thickness: 2px; text-underline-offset: 3px; }}
    svg text.asset-search-current, svg tspan.asset-search-current {{ fill: #ff2a3d !important; stroke: none !important; filter: none; font-weight: 800 !important; text-decoration: underline; text-decoration-thickness: 2px; text-underline-offset: 3px; }}
    @keyframes focus-dash-flow {{ from {{ stroke-dashoffset: 0; }} to {{ stroke-dashoffset: -17; }} }}
    @keyframes focus-dash-flow-reverse {{ from {{ stroke-dashoffset: 0; }} to {{ stroke-dashoffset: 17; }} }}
    @keyframes focus-arrow-pulse {{ 0%, 100% {{ opacity: .55; }} 50% {{ opacity: .9; }} }}
    @keyframes story-target-flash {{ 0% {{ box-shadow: 0 0 0 0 rgba(9,105,218,.75), inset 0 0 0 3px rgba(9,105,218,.8); filter: saturate(1.28) brightness(1.03); }} 55% {{ box-shadow: 0 0 0 10px rgba(9,105,218,.22), inset 0 0 0 2px rgba(9,105,218,.5); filter: saturate(1.12) brightness(1.01); }} 100% {{ box-shadow: 0 0 0 16px rgba(9,105,218,0), inset 0 0 0 0 rgba(9,105,218,0); filter: saturate(1) brightness(1); }} }}
    @keyframes code-target-overlay-flash {{ 0% {{ opacity: 1; transform: scale(1.004); box-shadow: 0 0 0 0 rgba(9,105,218,.42), 0 0 0 2px rgba(9,105,218,.32); }} 70% {{ opacity: .96; box-shadow: 0 0 0 8px rgba(9,105,218,.18), 0 0 0 2px rgba(9,105,218,.22); }} 100% {{ opacity: 0; transform: scale(1); box-shadow: 0 0 0 12px rgba(9,105,218,0), 0 0 0 0 rgba(9,105,218,0); }} }}
    @media (prefers-reduced-motion: reduce) {{
      svg line.asset-focus-connector, svg path.asset-focus-connector, svg polyline.asset-focus-connector, svg polygon.asset-focus-connector {{ animation: none; }}
      .story-target-flash, .code-target-flash-overlay {{ animation: none; }}
    }}
    @media (min-width: 1800px) {{
      :root {{
        --nav-width: 460px;
        --brand-height: 260px;
        --brand-mark-size: 176px;
        --brand-title-size: 84px;
        --brand-subtitle-size: 42px;
        --content-width: 1500px;
        --screen-body-font: 20px;
        --screen-code-font: 16px;
      }}
    }}
    @media (max-width: 1500px) {{
      :root {{
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
      }}
      header, section {{ padding: 16px; }}
      .story-steps {{ grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }}
      .num {{ width: 56px; padding: 0 8px !important; }}
      tr.comment-row td {{ background: linear-gradient(to right, var(--comment-row-bg) 0 96px, transparent 96px); }}
      .review-comment {{ margin-left: 96px; }}
    }}
    @media (max-width: 1280px) {{
      :root {{
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
      }}
      .review-nav {{ padding-right: 10px; }}
      .review-nav-head button {{ min-width: 86px; }}
      .story-steps {{ grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }}
      .story-step {{ grid-template-columns: 28px minmax(0, 1fr); padding: 7px 8px; }}
    }}
    @media (max-width: 1100px) {{
      :root {{
        --nav-width: 0px;
        --screen-body-font: 16px;
        --screen-code-font: 13px;
        --content-width: 100%;
      }}
      body {{ font-size: var(--scaled-body-font); }}
      main {{ width: calc(100% - 16px); max-width: calc(100vw - 16px); margin: 8px auto 16px; }}
      header, section, .file, .asset-inventory {{ width: 100%; margin-left: 0; margin-right: 0; }}
      .report-brand {{ display: none; }}
      .report-settings-launcher {{ right: 24px; bottom: calc(24px + var(--floating-control-size) + 10px); }}
      .review-nav {{ position: static; width: calc(100% - 16px); max-height: 38vh; margin: 8px auto 16px; }}
      .review-nav-resizer {{ display: none; }}
      .story {{ top: 0; }}
      .story-steps {{ grid-template-columns: repeat(auto-fit, minmax(148px, 1fr)); }}
      .diagram-dialog {{ inset: 12px; }}
      .diagram-toolbar {{ align-items: flex-start; flex-wrap: wrap; }}
      .diagram-tools {{ flex-wrap: wrap; justify-content: flex-end; }}
      .diagram-tools input {{ width: min(220px, calc(100vw - 48px)); }}
    }}
  </style>
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

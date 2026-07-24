from __future__ import annotations

import html


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
      --panel: #ffffff;
      --panel-subtle: #f8f8f8;
      --meta-panel: #ffffff;
      --meta-border: #d0d0d0;
      --meta-label: #57606a;
      --meta-text: #1f1f1f;
      --story-step-bg: #f6f8fa;
      --story-step-border: #8c959f;
      --story-step-hover-bg: #eef6ff;
      --story-step-active-bg: #dbeafe;
      --story-step-active-border: #0969da;
      --stat-add: #1a7f37;
      --stat-del: #cf222e;
      --border: #d0d0d0;
      --text: #1f1f1f;
      --muted: #616161;
      --link: #007acc;
      --button-bg: #ffffff;
      --button-hover-bg: #e5f1fb;
      --row-bg: #ffffff;
      --header-bg: #f3f3f3;
      --add-bg: #e6f4ea;
      --del-bg: #fde7e9;
      --hunk-bg: #e5f1fb;
      --comment-bg: #fff4ce;
      --comment-border: #ca5010;
      --comment-target-bg: #fff8dc;
      --comment-target-mix: rgba(255,244,206,.58);
      --comment-row-bg: rgba(255,248,220,.82);
      --comment-title-bg: rgba(255,255,255,.44);
      --comment-title-border: rgba(202,80,16,.34);
      --comment-panel-border: rgba(202,80,16,.55);
      --code-bg: #f8f8f8;
      --brand-panel: rgba(255,255,255,.9);
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
      --nav-width: 430px;
      --left-chrome-x: 42px;
      --left-chrome-width: calc(var(--nav-width) - 68px);
      --story-offset: 0px;
      --screen-body-font: clamp(22px, 0.65cm, 30px);
      --screen-code-font: clamp(18px, 0.52cm, 24px);
      --content-offset-width: 1360px;
      --content-width: 1260px;
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
    body {{ margin: 0; background: var(--bg); color: var(--text); font: var(--screen-body-font)/1.52 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    main {{ width: calc(100% - var(--nav-width) - 24px); max-width: calc(100vw - var(--nav-width) - 24px); min-width: 0; margin: 8px 8px 16px calc(var(--nav-width) + 16px); }}
    .report-brand {{ position: fixed; left: 8px; top: 8px; z-index: 4; display: flex; align-items: flex-start; justify-content: center; width: var(--nav-width); height: max(250px, calc(var(--story-offset) - 16px)); padding-top: 16px; pointer-events: none; color: var(--brand-text); }}
    .report-brand::before {{ content: ""; position: absolute; inset: 0; height: 250px; border-radius: 10px; background: var(--brand-panel); box-shadow: 0 10px 24px var(--shadow); }}
    .report-brand-inner {{ position: relative; display: grid; grid-template-columns: 144px minmax(0, 1fr); align-items: center; gap: 24px; width: 100%; height: 176px; padding: 16px 28px; font-weight: 800; letter-spacing: 0; }}
    .report-brand-mark {{ display: flex; align-items: center; justify-content: center; width: 144px; height: 144px; border-radius: 10px; background: #0969da; color: #fff; font: 800 92px/1 ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .report-brand-text {{ display: grid; gap: 2px; min-width: 0; line-height: 1.05; }}
    .report-brand-title {{ font-size: 80px; white-space: nowrap; }}
    .report-brand-subtitle {{ color: var(--muted); font-size: 40px; white-space: nowrap; }}
    .settings-launcher {{ position: fixed; left: 24px; top: 206px; z-index: 40; width: calc(var(--nav-width) - 32px); }}
    .settings-toggle {{ display: inline-flex; align-items: center; justify-content: center; width: 100%; height: 34px; padding: 0 18px; border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--link); box-shadow: none; cursor: pointer; font: 800 18px/1 ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .settings-toggle:hover {{ border-color: var(--link); box-shadow: 0 12px 32px rgba(9,105,218,.22); }}
    .settings-modal[hidden] {{ display: none; }}
    .settings-modal {{ position: fixed; inset: 0; z-index: 1100; }}
    .settings-backdrop {{ position: absolute; inset: 0; background: var(--overlay-bg); }}
    .settings-dialog {{ position: absolute; left: 50%; top: 50%; display: grid; gap: 18px; width: min(460px, calc(100vw - 40px)); max-height: calc(100vh - 40px); overflow: auto; transform: translate(-50%, -50%); padding: 20px; border: 1px solid var(--border); border-radius: 8px; background: var(--panel); color: var(--text); box-shadow: 0 18px 58px rgba(0,0,0,.42); }}
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
    .settings-option.is-active {{ border-color: var(--link); background: var(--button-hover-bg); color: var(--link); box-shadow: inset 3px 0 0 var(--link); }}
    .copy-context-menu[hidden] {{ display: none; }}
    .copy-context-menu {{ position: fixed; z-index: 1200; min-width: 178px; padding: 6px; border: 1px solid var(--border); border-radius: 8px; background: var(--panel); box-shadow: 0 12px 32px var(--shadow); }}
    .copy-context-menu button {{ display: flex; align-items: center; justify-content: flex-start; width: 100%; min-height: 32px; padding: 0 10px; border: 0; border-radius: 6px; background: transparent; color: var(--text); cursor: pointer; font: 700 14px/1.2 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; text-align: left; }}
    .copy-context-menu button:hover, .copy-context-menu button:focus-visible {{ background: var(--button-hover-bg); color: var(--link); outline: none; }}
    header, section, .file {{ width: min(100%, var(--content-width)); max-width: 100%; min-width: 0; margin-right: auto; margin-left: max(0px, calc((100% - var(--content-offset-width)) / 4)); background: var(--panel); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 16px; }}
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
    .diff-stats strong {{ display: block; margin-top: 4px; font: 800 calc(var(--screen-code-font) * 1.08)/1.2 ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .diff-stat-add {{ color: var(--stat-add); }}
    .diff-stat-del {{ color: var(--stat-del); }}
    code {{ background: rgba(175,184,193,.2); border-radius: 4px; padding: 1px 5px; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }}
    pre.stat {{ max-width: 100%; margin: 10px 0 0; padding: 12px; background: var(--code-bg); border-radius: 6px; overflow-x: auto; white-space: pre-wrap; overflow-wrap: anywhere; }}
    .label {{ display: block; color: var(--meta-label); font-size: .72rem; text-transform: uppercase; letter-spacing: .04em; margin-bottom: 3px; }}
    .toc a {{ display: inline-block; margin: 0 8px 8px 0; color: var(--link); text-decoration: none; }}
    .toc a:hover {{ text-decoration: underline; }}
    .review-nav {{ position: fixed; left: 8px; top: max(270px, var(--story-offset)); bottom: 8px; z-index: 8; width: var(--nav-width); margin: 0; padding: 10px 14px 10px 10px; overflow: auto; box-shadow: 0 8px 22px rgba(31,35,40,.10); }}
    .review-nav-head {{ position: sticky; top: -10px; z-index: 2; display: flex; align-items: center; justify-content: space-between; gap: 8px; margin: -10px -14px 8px -10px; padding: 10px 14px 8px 10px; background: var(--panel); border-bottom: 1px solid var(--border); box-shadow: 0 2px 0 var(--panel); }}
    .review-nav h2 {{ margin: 0; font-size: .86em; }}
    .review-nav-head button {{ display: inline-flex; align-items: center; justify-content: center; min-width: 102px; height: 28px; padding: 0 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); cursor: pointer; font: var(--screen-code-font)/1 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
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
    .review-nav-resizer {{ position: fixed; left: calc(var(--nav-width) + 5px); top: max(270px, var(--story-offset)); bottom: 8px; width: 10px; cursor: ew-resize; z-index: 20; }}
    .review-nav-resizer::before {{ content: ""; position: absolute; inset: 0 3px; border-radius: 99px; background: transparent; }}
    .review-nav-resizer:hover::before, body.is-resizing-review-nav .review-nav-resizer::before {{ background: rgba(9,105,218,.38); }}
    body.is-resizing-review-nav {{ cursor: ew-resize; user-select: none; }}
    .story {{ position: sticky; top: 0; z-index: 12; padding: 10px 12px; margin-bottom: 0; border-bottom: 0; border-bottom-left-radius: 0; border-bottom-right-radius: 0; box-shadow: 0 8px 22px rgba(31,35,40,.08); }}
    .story h2 {{ margin: 0; font-size: var(--screen-code-font); }}
    .story-controls {{ display: flex; align-items: center; justify-content: flex-end; gap: 6px; margin: -22px 0 8px; }}
    .story-controls button {{ display: inline-flex; align-items: center; justify-content: center; min-width: 54px; height: 28px; padding: 0 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--button-bg); color: var(--text); cursor: pointer; font: inherit; line-height: 1; }}
    .story-controls button:hover {{ border-color: var(--link); color: var(--link); }}
    .to-top-button {{ position: fixed; right: 24px; bottom: 24px; z-index: 32; display: inline-flex; align-items: center; justify-content: center; width: 58px; height: 58px; border: 1px solid var(--border); border-radius: 999px; background: var(--button-bg); color: var(--link); box-shadow: 0 10px 28px var(--shadow); cursor: pointer; opacity: 0; visibility: hidden; pointer-events: none; transform: translateY(10px) scale(.96); transition: opacity .18s ease, transform .18s ease, visibility 0s linear .18s, border-color .12s ease, box-shadow .12s ease; font-size: 0; }}
    .to-top-button::before {{ content: ""; width: 15px; height: 15px; border-left: 4px solid currentColor; border-top: 4px solid currentColor; transform: translateY(4px) rotate(45deg); border-radius: 2px; }}
    .to-top-button:hover {{ border-color: var(--link); box-shadow: 0 12px 32px rgba(9,105,218,.22); transform: translateY(0) scale(1.03); }}
    body.has-left-top .to-top-button {{ opacity: 1; visibility: visible; pointer-events: auto; transform: translateY(0) scale(1); transition-delay: 0s; }}
    #story-counter {{ color: var(--muted); min-width: 44px; text-align: center; font-size: var(--screen-code-font); }}
    .story-steps {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); align-items: stretch; gap: 6px; margin: 0; padding: 0; list-style: none; }}
    .story-steps li {{ min-width: 0; }}
    .story-step {{ display: grid; grid-template-columns: 34px minmax(0, 1fr); gap: 7px; align-items: center; width: 100%; height: 100%; min-height: 44px; padding: 8px 10px; border: 1px solid var(--story-step-border); border-radius: 6px; background: var(--story-step-bg); color: var(--text); text-align: left; cursor: pointer; font: inherit; box-shadow: 0 1px 0 rgba(31,35,40,.08); transition: background .12s ease, border-color .12s ease, box-shadow .12s ease, transform .12s ease; }}
    .story-step:hover {{ border-color: var(--story-step-active-border); background: var(--story-step-hover-bg); box-shadow: 0 0 0 2px rgba(9,105,218,.18); transform: translateY(-1px); }}
    .story-step:focus-visible {{ outline: 2px solid var(--story-step-active-border); outline-offset: 2px; }}
    .story-step.is-active {{ border-color: var(--story-step-active-border); background: var(--story-step-active-bg); box-shadow: inset 4px 0 0 var(--story-step-active-border), 0 0 0 1px color-mix(in srgb, var(--story-step-active-border) 34%, transparent); }}
    .story-step-index {{ color: var(--story-step-active-border); font: 800 var(--screen-code-font)/1.35 ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .story-step-text {{ display: grid; gap: 3px; min-width: 0; }}
    .story-step-text strong {{ display: -webkit-box; overflow: hidden; overflow-wrap: anywhere; -webkit-box-orient: vertical; -webkit-line-clamp: 2; font-size: var(--screen-code-font); line-height: 1.25; }}
    .story-details {{ min-width: 0; max-width: 100%; margin-top: 7px; border: 1px solid var(--border); border-radius: 6px; background: var(--panel-subtle); }}
    .story-details-title {{ padding: 7px 8px; font-size: var(--screen-code-font); font-weight: 700; }}
    .story-details div:not(.story-details-title) {{ padding: 0 8px 8px; color: var(--muted); font-size: var(--screen-code-font); line-height: 1.35; white-space: pre-line; overflow-wrap: anywhere; }}
    .asset-inventory {{ width: min(100%, var(--content-width)); max-width: 100%; min-width: 0; margin-right: auto; margin-left: max(0px, calc((100% - var(--content-offset-width)) / 4)); background: var(--panel); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 16px; }}
    .asset-inventory summary {{ display: flex; align-items: center; gap: 10px; padding: 14px 20px; font-size: 20px; font-weight: 700; line-height: 1.2; cursor: pointer; user-select: none; }}
    .asset-inventory summary:hover {{ color: var(--link); background: var(--button-hover-bg); }}
    .asset-inventory summary:focus-visible {{ outline: 2px solid var(--link); outline-offset: 2px; }}
    .asset-inventory summary::before {{ content: ">"; color: var(--link); font: 800 var(--screen-code-font)/1 ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .asset-inventory[open] summary {{ border-bottom: 1px solid var(--border); }}
    .asset-inventory[open] summary::before {{ content: "v"; }}
    .asset-inventory .diagram-list {{ padding: 14px 20px 20px; }}
    .story-target-active {{ outline: 3px solid rgba(9,105,218,.35); outline-offset: 2px; scroll-margin-top: calc(var(--story-offset) + 72px); }}
    .story-target-flash {{ animation: story-target-flash .4s ease-out; }}
    tr.code-target-flash .code {{ animation: code-target-flash .4s ease-out; }}
    tr.code-target-flash .code {{ box-shadow: inset 4px 0 0 rgba(9,105,218,.85), inset -3px 0 0 rgba(9,105,218,.55); }}
    tr.code-target-flash-start .code {{ box-shadow: inset 4px 0 0 rgba(9,105,218,.85), inset -3px 0 0 rgba(9,105,218,.55), inset 0 3px 0 rgba(9,105,218,.75); }}
    tr.code-target-flash-end .code {{ box-shadow: inset 4px 0 0 rgba(9,105,218,.85), inset -3px 0 0 rgba(9,105,218,.55), inset 0 -3px 0 rgba(9,105,218,.45); }}
    tr.code-target-flash-start.code-target-flash-end .code {{ box-shadow: inset 4px 0 0 rgba(9,105,218,.85), inset -3px 0 0 rgba(9,105,218,.55), inset 0 3px 0 rgba(9,105,218,.75), inset 0 -3px 0 rgba(9,105,218,.45); }}
    .file, .file-comment, .review-comment, tr[id] {{ scroll-margin-top: calc(var(--story-offset) + 72px); }}
    .file-header {{ margin: -1px -1px 0; padding: 10px 13px; border-bottom: 1px solid var(--border); background: var(--header-bg); font-weight: 700; position: sticky; top: calc(var(--story-offset) - 2px); z-index: 6; box-shadow: 0 1px 0 var(--border); }}
    .file-comment {{ min-width: 0; max-width: calc(100% - 24px); margin: 6px 12px 6px; padding: 8px 12px; border-left: 4px solid var(--comment-border); background: var(--comment-bg); border-radius: 6px; overflow-wrap: anywhere; }}
    table.diff {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: var(--screen-code-font); line-height: 1.5; }}
    .diff td {{ vertical-align: top; border: 0; padding: 0; }}
    .num {{ width: 64px; padding: 0 10px !important; color: var(--muted); text-align: right; user-select: none; border-right: 1px solid var(--border) !important; }}
    .code {{ white-space: pre-wrap; overflow-wrap: anywhere; padding: 0 10px !important; }}
    tr.add .num, tr.add .code {{ background: var(--add-bg); }}
    tr.del .num, tr.del .code {{ background: var(--del-bg); }}
    tr.ctx .num, tr.ctx .code {{ background: var(--row-bg); }}
    tr.hunk .num, tr.hunk .code {{ background: var(--hunk-bg); color: #0969da; }}
    tr.header .num, tr.header .code {{ background: var(--header-bg); color: var(--muted); font-weight: 700; }}
    tr.comment-target .num, tr.comment-target .code {{ background: var(--comment-target-bg); }}
    tr.comment-target.add .num, tr.comment-target.add .code {{ background: linear-gradient(to right, var(--comment-target-mix), var(--comment-target-mix)), var(--add-bg); }}
    tr.comment-target .num:first-child {{ box-shadow: inset 4px 0 0 var(--comment-border); }}
    tr.comment-target-start .num, tr.comment-target-start .code {{ box-shadow: inset 0 1px 0 rgba(212,167,44,.55); }}
    tr.comment-target-end .num, tr.comment-target-end .code {{ box-shadow: inset 0 -1px 0 rgba(212,167,44,.35); }}
    tr.comment-target-start .num:first-child {{ box-shadow: inset 4px 0 0 var(--comment-border), inset 0 1px 0 rgba(212,167,44,.55); }}
    tr.comment-target-end .num:first-child {{ box-shadow: inset 4px 0 0 var(--comment-border), inset 0 -1px 0 rgba(212,167,44,.35); }}
    tr.comment-target-single .num:first-child {{ box-shadow: inset 4px 0 0 var(--comment-border), inset 0 1px 0 rgba(212,167,44,.55), inset 0 -1px 0 rgba(212,167,44,.35); }}
    tr.comment-row td {{ background: linear-gradient(to right, var(--comment-row-bg) 0 112px, transparent 112px); padding: 0 !important; }}
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
    .diagram-code-link-code {{ display: block; max-height: none; overflow: visible; padding: 8px; border-radius: 4px; background: var(--code-bg); font: var(--screen-code-font)/1.45 ui-monospace, SFMono-Regular, Consolas, monospace; white-space: pre-wrap; overflow-wrap: anywhere; }}
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
    svg .asset-search-match {{ fill: #cf222e; stroke: #cf222e; }}
    svg .asset-search-current {{ filter: drop-shadow(0 0 3px #fb8500); }}
    @keyframes focus-dash-flow {{ from {{ stroke-dashoffset: 0; }} to {{ stroke-dashoffset: -17; }} }}
    @keyframes focus-dash-flow-reverse {{ from {{ stroke-dashoffset: 0; }} to {{ stroke-dashoffset: 17; }} }}
    @keyframes focus-arrow-pulse {{ 0%, 100% {{ opacity: .55; }} 50% {{ opacity: .9; }} }}
    @keyframes story-target-flash {{ 0% {{ box-shadow: 0 0 0 0 rgba(9,105,218,.75), inset 0 0 0 3px rgba(9,105,218,.8); filter: saturate(1.28) brightness(1.03); }} 55% {{ box-shadow: 0 0 0 10px rgba(9,105,218,.22), inset 0 0 0 2px rgba(9,105,218,.5); filter: saturate(1.12) brightness(1.01); }} 100% {{ box-shadow: 0 0 0 16px rgba(9,105,218,0), inset 0 0 0 0 rgba(9,105,218,0); filter: saturate(1) brightness(1); }} }}
    @keyframes code-target-flash {{ 0% {{ outline: 3px solid rgba(9,105,218,.85); outline-offset: -2px; filter: saturate(1.28) brightness(1.03); font-weight: 800; }} 45% {{ outline: 2px solid rgba(9,105,218,.55); outline-offset: -1px; filter: saturate(1.16) brightness(1.01); font-weight: 650; }} 100% {{ outline: 0 solid rgba(9,105,218,0); outline-offset: 0; filter: saturate(1) brightness(1); font-weight: 400; }} }}
    @media (prefers-reduced-motion: reduce) {{
      svg line.asset-focus-connector, svg path.asset-focus-connector, svg polyline.asset-focus-connector, svg polygon.asset-focus-connector {{ animation: none; }}
      .story-target-flash, tr.code-target-flash .code {{ animation: none; }}
    }}
    @media (max-width: 1100px) {{
      body {{ font-size: 18px; }}
      main {{ width: calc(100% - 16px); margin: 8px auto 16px; }}
      .report-brand {{ display: none; }}
      .settings-launcher {{ left: auto; right: 16px; top: 16px; z-index: 40; width: min(280px, calc(100vw - 32px)); }}
      .review-nav {{ position: static; width: calc(100% - 16px); max-height: 38vh; margin: 8px auto 16px; }}
      .review-nav-resizer {{ display: none; }}
      .story {{ top: 0; }}
    }}
  </style>
</head>
<body>
<div class="report-brand" aria-hidden="true"><div class="report-brand-inner"><span class="report-brand-mark">AI</span><span class="report-brand-text"><span class="report-brand-title">Diff</span><span class="report-brand-subtitle">report</span></span></div></div>
<div class="settings-launcher">
  <button type="button" class="settings-toggle" data-settings-toggle aria-haspopup="dialog" aria-expanded="false">Settings</button>
</div>
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
    </div>
  </div>
</div>
<div class="copy-context-menu" data-copy-markdown-menu hidden>
  <button type="button" data-copy-plain-action>Copy</button>
  <button type="button" data-copy-markdown-action>Copy as Markdown</button>
</div>
"""


def theme_script() -> str:
    return """<script>
(function () {
  const themeKey = "codex-diff-report-theme";
  const root = document.documentElement;
  const toggle = document.querySelector("[data-settings-toggle]");
  const modal = document.querySelector("[data-settings-modal]");
  const closeButtons = Array.from(document.querySelectorAll("[data-settings-close]"));
  const themeOptions = Array.from(document.querySelectorAll("[data-theme-value]"));

  function currentTheme() {
    return root.dataset.theme === "dark" ? "dark" : "light";
  }

  function applyTheme(theme, persist) {
    const nextTheme = theme === "dark" ? "dark" : "light";
    root.dataset.theme = nextTheme;
    for (const option of themeOptions) {
      const active = option.dataset.themeValue === nextTheme;
      option.classList.toggle("is-active", active);
      option.setAttribute("aria-pressed", active ? "true" : "false");
    }
    if (persist) {
      try {
        localStorage.setItem(themeKey, nextTheme);
      } catch (error) {
        // Ignore storage failures, for example in restricted file viewers.
      }
    }
  }

  function setSettingsOpen(open) {
    if (!modal || !toggle) {
      return;
    }
    modal.hidden = !open;
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      const close = modal.querySelector("[data-settings-close].settings-close");
      if (close) {
        close.focus();
      }
    } else {
      toggle.focus();
    }
  }

  applyTheme(currentTheme(), false);

  if (toggle) {
    toggle.addEventListener("click", function (event) {
      event.preventDefault();
      setSettingsOpen(!modal || modal.hidden);
    });
  }
  for (const closeButton of closeButtons) {
    closeButton.addEventListener("click", function () {
      setSettingsOpen(false);
    });
  }
  for (const option of themeOptions) {
    option.addEventListener("click", function () {
      applyTheme(option.dataset.themeValue, true);
    });
  }
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && modal && !modal.hidden) {
      setSettingsOpen(false);
    }
  });
  window.addEventListener("storage", function (event) {
    if (event.key === themeKey) {
      applyTheme(event.newValue === "dark" ? "dark" : "light", false);
    }
  });
}());
</script>
"""


def story_script() -> str:
    return """<script>
(function () {
  const steps = Array.from(document.querySelectorAll("[data-story-index]"));
  const counter = document.getElementById("story-counter");
  const detailsTitle = document.getElementById("story-details-title");
  const detailsBody = document.getElementById("story-details-body");
  const jumpDurationMs = 0;
  let activeIndex = 0;
  let activeTarget = null;
  let activeScrollTimer = 0;
  let activeScrollEndTimer = 0;
  let activeFlashClearTimer = 0;
  let navigationToken = 0;
  let topStateRaf = 0;
  if ("scrollRestoration" in history) {
    history.scrollRestoration = "manual";
  }

  function initReviewNavResize() {
    const nav = document.getElementById("review-comments");
    const resizer = nav ? nav.querySelector(".review-nav-resizer") : null;
    if (!nav || !resizer) {
      return;
    }
    let resizing = false;
    const defaultWidth = 430;

    function applyWidth(width) {
      const maxWidth = Math.max(320, Math.min(window.innerWidth * 0.58, 820));
      const nextWidth = Math.max(280, Math.min(maxWidth, width));
      document.documentElement.style.setProperty("--nav-width", nextWidth + "px");
    }

    resizer.addEventListener("pointerdown", function (event) {
      if (event.button !== 0 || window.matchMedia("(max-width: 1100px)").matches) {
        return;
      }
      resizing = true;
      document.body.classList.add("is-resizing-review-nav");
      event.preventDefault();
    });

    resizer.addEventListener("dblclick", function (event) {
      applyWidth(defaultWidth);
      event.preventDefault();
    });

    document.addEventListener("pointermove", function (event) {
      if (!resizing) {
        return;
      }
      if (event.buttons !== 1) {
        stopResize();
        return;
      }
      applyWidth(event.clientX - 8);
      event.preventDefault();
    });

    function stopResize(event) {
      if (!resizing) {
        return;
      }
      resizing = false;
      document.body.classList.remove("is-resizing-review-nav");
    }

    document.addEventListener("pointerup", stopResize);
    document.addEventListener("pointercancel", stopResize);
    window.addEventListener("blur", stopResize);
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) {
        stopResize();
      }
    });
  }

  function initReviewNavTree() {
    const nav = document.getElementById("review-comments");
    if (!nav) {
      return;
    }
    nav.addEventListener("click", function (event) {
      const toggle = event.target.closest(".review-nav-toggle");
      if (!toggle || !nav.contains(toggle)) {
        return;
      }
      const node = toggle.closest(".review-nav-node");
      if (!node) {
        return;
      }
      const nextOpen = !node.classList.contains("is-open");
      event.preventDefault();
      event.stopPropagation();
      node.classList.toggle("is-open", nextOpen);
      toggle.setAttribute("aria-expanded", nextOpen ? "true" : "false");
    });
  }

  function resetReviewNavTree() {
    const nav = document.getElementById("review-comments");
    if (!nav) {
      return;
    }
    for (const node of nav.querySelectorAll(".review-nav-node")) {
      const isFile = node.classList.contains("review-nav-file");
      const shouldOpen = !isFile || node.classList.contains("review-nav-passthrough");
      node.classList.toggle("is-open", shouldOpen);
      const toggle = node.querySelector(":scope > .review-nav-row .review-nav-toggle");
      if (toggle) {
        toggle.setAttribute("aria-expanded", shouldOpen ? "true" : "false");
      }
    }
    nav.scrollTop = 0;
    nav.scrollLeft = 0;
  }

  function initReviewNavActiveFile() {
    const nav = document.getElementById("review-comments");
    const files = Array.from(document.querySelectorAll("article.file[data-file]"));
    if (!nav || !files.length) {
      return;
    }
    const navItemsByAnchor = new Map();
    for (const link of nav.querySelectorAll('.review-nav-file > .review-nav-row a[href^="#"]')) {
      const anchor = decodeURIComponent(String(link.getAttribute("href") || "").replace(/^#/, ""));
      const item = link.closest(".review-nav-file");
      if (anchor && item) {
        navItemsByAnchor.set(anchor, item);
      }
    }
    let activeItem = null;
    let activeRaf = 0;

    function revealActiveItem(item) {
      let parent = item.parentElement ? item.parentElement.closest(".review-nav-dir") : null;
      while (parent) {
        parent.classList.add("is-open");
        const toggle = parent.querySelector(":scope > .review-nav-row .review-nav-toggle");
        if (toggle) {
          toggle.setAttribute("aria-expanded", "true");
        }
        parent = parent.parentElement ? parent.parentElement.closest(".review-nav-dir") : null;
      }
      item.scrollIntoView({ block: "nearest", inline: "nearest" });
    }

    function setActiveFile(article) {
      const nextItem = article ? navItemsByAnchor.get(article.id) || null : null;
      if (nextItem === activeItem) {
        return;
      }
      if (activeItem) {
        activeItem.classList.remove("is-current");
      }
      activeItem = nextItem;
      if (activeItem) {
        activeItem.classList.add("is-current");
        revealActiveItem(activeItem);
      }
    }

    function updateActiveFile() {
      activeRaf = 0;
      const story = document.getElementById("story");
      const probeY = Math.min(
        Math.max((story ? story.offsetHeight : 0) + 80, 120),
        window.innerHeight * 0.45
      );
      let candidate = null;
      let fallback = null;
      for (const file of files) {
        const rect = file.getBoundingClientRect();
        if (rect.bottom <= probeY || rect.top >= window.innerHeight) {
          continue;
        }
        if (rect.top <= probeY) {
          candidate = file;
        } else if (!fallback) {
          fallback = file;
        }
      }
      setActiveFile(candidate || fallback);
    }

    function scheduleActiveFileUpdate() {
      if (activeRaf) {
        return;
      }
      activeRaf = window.requestAnimationFrame(updateActiveFile);
    }

    window.addEventListener("scroll", scheduleActiveFileUpdate, { passive: true });
    window.addEventListener("resize", scheduleActiveFileUpdate);
    scheduleActiveFileUpdate();
  }

  function updateStoryOffset() {
    const story = document.getElementById("story");
    const offset = story ? Math.ceil(story.getBoundingClientRect().height) : 0;
    document.documentElement.style.setProperty("--story-offset", offset + "px");
  }

  function updateTopButtonState() {
    if (topStateRaf) {
      return;
    }
    topStateRaf = window.requestAnimationFrame(function () {
      topStateRaf = 0;
      document.body.classList.toggle("has-left-top", window.scrollY > 24);
    });
  }

  function setActive(index) {
    if (!steps.length) {
      return;
    }
    activeIndex = Math.max(0, Math.min(steps.length - 1, index));
    steps.forEach(function (step, stepIndex) {
      step.classList.toggle("is-active", stepIndex === activeIndex);
    });
    if (counter) {
      counter.textContent = (activeIndex + 1) + " / " + steps.length;
    }
    const step = steps[activeIndex];
    document.body.dataset.activeStoryTitle = step.dataset.storyTitle || "";
    document.body.dataset.activeStoryBody = step.dataset.storyBody || "";
    if (detailsTitle) {
      detailsTitle.textContent = step.dataset.storyTitle || "Details";
    }
    if (detailsBody) {
      detailsBody.textContent = step.dataset.storyBody || "";
    }
  }

  function clearTargetHighlight() {
    if (activeTarget) {
      activeTarget.classList.remove("story-target-active");
      activeTarget = null;
    }
    clearFlashTargets();
  }

  function openStep(index) {
    if (!steps.length) {
      return;
    }
    setActive(index);
    const step = steps[activeIndex];
    clearTargetHighlight();

    const targetId = step.dataset.storyTarget || "";
    jumpToStoryTarget(step, targetId);
  }

  function jumpToStoryTarget(step, targetId) {
    if (targetId) {
      const target = document.getElementById(targetId);
      if (target) {
        activeTarget = target;
        target.classList.add("story-target-active");
        animateWindowScrollToElement(target, jumpDurationMs);
      }
    } else {
      animateWindowScrollToElement(step, jumpDurationMs);
    }
  }

  function jumpToHash(hash, updateUrl) {
    const targetId = decodeURIComponent(String(hash || "").replace(/^#/, ""));
    if (!targetId) {
      return false;
    }
    const target = document.getElementById(targetId);
    if (!target) {
      return false;
    }
    clearTargetHighlight();
    activeTarget = target;
    target.classList.add("story-target-active");
    animateWindowScrollToElement(target, jumpDurationMs);
    if (updateUrl && history.replaceState) {
      history.replaceState(null, "", location.pathname + location.search);
    }
    return true;
  }

  function jumpToTop() {
    clearTargetHighlight();
    navigationToken += 1;
    animateWindowScrollToY(0, jumpDurationMs, navigationToken);
    const nav = document.getElementById("review-comments");
    if (nav) {
      nav.scrollTop = 0;
      nav.scrollLeft = 0;
    }
    if (history.replaceState) {
      history.replaceState(null, "", location.pathname + location.search);
    }
    updateTopButtonState();
  }

  function resetPageScrollOnLoad() {
    const nav = document.getElementById("review-comments");
    window.scrollTo(0, 0);
    if (nav) {
      nav.scrollTop = 0;
      nav.scrollLeft = 0;
    }
    document.body.classList.remove("has-left-top");
  }

  function animateWindowScrollToElement(element, durationMs) {
    window.clearTimeout(activeScrollTimer);
    window.clearTimeout(activeScrollEndTimer);
    navigationToken += 1;
    const token = navigationToken;
    const startY = window.scrollY;
    const scrollElement = scrollContextElement(element);
    const rect = scrollElement.getBoundingClientRect();
    const safeTop = scrollSafeTop();
    const maxY = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    const targetY = Math.max(0, Math.min(maxY, startY + rect.top - safeTop));
    animateWindowScrollToY(targetY, durationMs, token, function () {
      flashTargets(element, scrollElement);
    });
  }

  function scrollSafeTop() {
    const value = getComputedStyle(document.documentElement).getPropertyValue("--story-offset");
    const storyOffset = Number.parseFloat(value || "0");
    return (Number.isFinite(storyOffset) ? storyOffset : 0) + 72;
  }

  function scrollContextElement(element) {
    if (!element || !element.classList || !element.classList.contains("review-comment")) {
      return element;
    }
    const row = element.closest("tr.comment-row");
    if (!row) {
      return element;
    }
    let context = row;
    let visibleLines = 0;
    let cursor = row.previousElementSibling;
    while (cursor && visibleLines < 3) {
      if (cursor.matches("tr[id], tr.add, tr.ctx, tr.del")) {
        context = cursor;
        visibleLines += 1;
      }
      cursor = cursor.previousElementSibling;
    }
    return context;
  }

  function flashTargets(element, contextElement) {
    clearFlashTargets();
    const commentTargets = element && element.classList && element.classList.contains("review-comment")
      ? [element]
      : [];
    const codeTargets = codeFlashTargets(element, contextElement);
    for (const target of commentTargets) {
      target.classList.remove("story-target-flash");
      void target.offsetWidth;
      target.classList.add("story-target-flash");
      activeFlashClearTimer = window.setTimeout(function () {
        target.classList.remove("story-target-flash");
      }, 460);
    }
    for (const target of codeTargets) {
      target.classList.remove("code-target-flash");
      target.classList.remove("code-target-flash-start");
      target.classList.remove("code-target-flash-end");
      void target.offsetWidth;
      target.classList.add("code-target-flash");
      activeFlashClearTimer = window.setTimeout(function () {
        target.classList.remove("code-target-flash");
        target.classList.remove("code-target-flash-start");
        target.classList.remove("code-target-flash-end");
      }, 460);
    }
  }

  function codeFlashTargets(element, contextElement) {
    if (element && element.dataset && element.dataset.commentFile) {
      const file = element.dataset.commentFile;
      const start = Number(element.dataset.commentRangeStart || element.dataset.commentLine || 0);
      const end = Number(element.dataset.commentRangeEnd || start);
      if (file && Number.isFinite(start) && Number.isFinite(end)) {
        const rows = Array.from(document.querySelectorAll("tr[data-file]")).filter(function (row) {
          const line = Number(row.dataset.newLine || 0);
          return row.dataset.file === file && line >= start && line <= end;
        });
        if (rows.length) {
          rows[0].classList.add("code-target-flash-start");
          rows[rows.length - 1].classList.add("code-target-flash-end");
        }
        return rows;
      }
    }
    const row = contextElement && contextElement.closest ? contextElement.closest("tr[data-file]") : null;
    if (row) {
      row.classList.add("code-target-flash-start");
      row.classList.add("code-target-flash-end");
      return [row];
    }
    return [];
  }

  function clearFlashTargets() {
    window.clearTimeout(activeFlashClearTimer);
    for (const target of document.querySelectorAll(".story-target-flash")) {
      target.classList.remove("story-target-flash");
    }
    for (const target of document.querySelectorAll(".code-target-flash")) {
      target.classList.remove("code-target-flash");
      target.classList.remove("code-target-flash-start");
      target.classList.remove("code-target-flash-end");
    }
  }

  function animateWindowScrollToY(targetY, durationMs, token, onDone) {
    window.clearTimeout(activeScrollTimer);
    window.clearTimeout(activeScrollEndTimer);
    const startY = window.scrollY;
    const maxY = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    targetY = Math.max(0, Math.min(maxY, targetY));
    const distance = targetY - startY;
    const startedAt = performance.now();
    if (durationMs <= 0) {
      window.scrollTo(0, targetY);
      updateTopButtonState();
      if (onDone) {
        onDone();
      }
      return;
    }
    if (!distance) {
      if (onDone) {
        onDone();
      }
      return;
    }
    function tick(now) {
      if (token && token !== navigationToken) {
        return;
      }
      const elapsed = Math.min(1, (now - startedAt) / durationMs);
      const eased = elapsed < 0.5
        ? 4 * elapsed * elapsed * elapsed
        : 1 - Math.pow(-2 * elapsed + 2, 3) / 2;
      window.scrollTo(0, startY + distance * eased);
      if (elapsed < 1) {
        activeScrollTimer = window.setTimeout(function () {
          tick(performance.now());
        }, 16);
      }
    }
    tick(performance.now());
    activeScrollEndTimer = window.setTimeout(function () {
      if (token && token !== navigationToken) {
        return;
      }
      window.scrollTo(0, targetY);
      updateTopButtonState();
      if (onDone) {
        onDone();
      }
    }, durationMs + 30);
  }

  document.addEventListener("click", function (event) {
    const nav = event.target.closest("[data-story-nav]");
    if (nav) {
      if (steps.length) {
        openStep(activeIndex + (nav.dataset.storyNav === "prev" ? -1 : 1));
      }
      return;
    }
    if (event.target.closest("[data-story-top]")) {
      event.preventDefault();
      jumpToTop();
      return;
    }
    if (event.target.closest("[data-review-nav-reset]")) {
      event.preventDefault();
      resetReviewNavTree();
      return;
    }
    const navFileLink = event.target.closest(".review-nav-file .review-nav-row a");
    if (navFileLink && jumpToHash(navFileLink.getAttribute("href"), true)) {
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    const anchor = event.target.closest('a[href^="#"]');
    if (anchor && jumpToHash(anchor.getAttribute("href"), true)) {
      event.preventDefault();
      return;
    }
    const step = event.target.closest("[data-story-index]");
    if (step) {
      const index = Number(step.dataset.storyIndex);
      if (Number.isFinite(index)) {
        event.stopPropagation();
        openStep(index);
      }
    }
  });

  document.addEventListener("keydown", function (event) {
    if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
      return;
    }
    if (!steps.length) {
      return;
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      openStep(activeIndex + 1);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      openStep(activeIndex - 1);
    }
  });

  initReviewNavResize();
  initReviewNavTree();
  initReviewNavActiveFile();
  updateStoryOffset();
  updateTopButtonState();
  resetPageScrollOnLoad();
  if (steps.length) {
    setActive(0);
  }
  if (location.hash && history.replaceState) {
    history.replaceState(null, "", location.pathname + location.search);
  }
  window.addEventListener("scroll", updateTopButtonState, { passive: true });
  window.addEventListener("resize", updateStoryOffset);
  window.addEventListener("pageshow", function () {
    updateStoryOffset();
    updateTopButtonState();
    resetPageScrollOnLoad();
  });
  window.setTimeout(function () {
    updateStoryOffset();
    updateTopButtonState();
    resetPageScrollOnLoad();
  }, 60);
}());
	</script>
	"""


def copy_selection_script() -> str:
    return """<script>
(function () {
  const menu = document.querySelector("[data-copy-markdown-menu]");
  const plainAction = document.querySelector("[data-copy-plain-action]");
  const action = document.querySelector("[data-copy-markdown-action]");
  let activeMarkdown = "";

  function selectionRange() {
    const selection = window.getSelection ? window.getSelection() : null;
    if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
      return null;
    }
    return selection.getRangeAt(0);
  }

  function intersects(range, node) {
    try {
      return range.intersectsNode(node);
    } catch (error) {
      return false;
    }
  }

  function rowFile(row) {
    const article = row.closest("article.file[data-file]");
    return article ? article.dataset.file || "" : "";
  }

  function selectedTextWithin(range, node) {
    if (!intersects(range, node)) {
      return "";
    }
    const nodeRange = document.createRange();
    nodeRange.selectNodeContents(node);
    const clipped = range.cloneRange();
    if (clipped.compareBoundaryPoints(Range.START_TO_START, nodeRange) < 0) {
      clipped.setStart(nodeRange.startContainer, nodeRange.startOffset);
    }
    if (clipped.compareBoundaryPoints(Range.END_TO_END, nodeRange) > 0) {
      clipped.setEnd(nodeRange.endContainer, nodeRange.endOffset);
    }
    if (clipped.collapsed) {
      return "";
    }
    const wrapper = document.createElement("div");
    wrapper.appendChild(clipped.cloneContents());
    for (const asset of wrapper.querySelectorAll(".diagram-preview-wrap, .log-preview")) {
      asset.remove();
    }
    return wrapper.textContent.trim();
  }

  function commentText(comment, range) {
    const body = comment.classList.contains("file-comment") ? comment : comment.querySelector(".body");
    return body ? selectedTextWithin(range, body) : "";
  }

  function quoteMarkdown(text) {
    if (!text) {
      return "";
    }
    return text.split(/\\r?\\n/).map(function (line) {
      return line ? "> " + line : ">";
    }).join("\\n");
  }

  function fileHeading(file) {
    return "### `" + String(file).replace(/`/g, "\\\\`") + "`";
  }

  function appendBlank(parts) {
    if (parts.length && parts[parts.length - 1] !== "") {
      parts.push("");
    }
  }

  function openFence(parts, state) {
    if (!state.inFence) {
      appendBlank(parts);
      parts.push("```diff");
      state.inFence = true;
    }
  }

  function closeFence(parts, state) {
    if (state.inFence) {
      parts.push("```");
      state.inFence = false;
    }
  }

  function appendFile(parts, state, file) {
    if (state.file === file) {
      return;
    }
    closeFence(parts, state);
    appendBlank(parts);
    parts.push(fileHeading(file || "diff"));
    state.file = file;
  }

  function buildMarkdown(range) {
    const nodes = Array.from(document.querySelectorAll("article.file .file-comment, article.file tr"));
    const selectedNodes = nodes.filter(function (node) {
      return intersects(range, node);
    });
    if (!selectedNodes.length) {
      return "";
    }

    const parts = [];
    const state = { file: null, inFence: false };
    for (const row of selectedNodes) {
      const file = rowFile(row);
      appendFile(parts, state, file);
      if (row.dataset.diffKind) {
        const code = row.querySelector(".code");
        if (code) {
          openFence(parts, state);
          parts.push(code.textContent);
        }
        continue;
      }

      const comment = row.classList.contains("file-comment")
        ? row
        : row.querySelector(".review-comment");
      if (!comment) {
        continue;
      }
      closeFence(parts, state);
      const title = comment.classList.contains("file-comment") ? null : comment.querySelector(".title");
      appendBlank(parts);
      if (title && intersects(range, title) && title.textContent.trim()) {
        parts.push("> **" + title.textContent.trim() + "**");
        parts.push(">");
      }
      const body = quoteMarkdown(commentText(comment, range));
      if (body) {
        parts.push(body);
      }
    }
    closeFence(parts, state);
    return parts.join("\\n").replace(/\\n{3,}/g, "\\n\\n").trim();
  }

  function hideMenu() {
    if (!menu) {
      return;
    }
    menu.hidden = true;
    activeMarkdown = "";
  }

  function fallbackCopy(text) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand("copy");
    } finally {
      textarea.remove();
    }
  }

  function copyMarkdown(text) {
    if (!text) {
      return Promise.resolve(false);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(function () {
        return true;
      }).catch(function () {
        fallbackCopy(text);
        return true;
      });
    }
    fallbackCopy(text);
    return Promise.resolve(true);
  }

  function copyPlainSelection() {
    if (menu) {
      menu.hidden = true;
    }
    document.execCommand("copy");
    activeMarkdown = "";
  }

  function showMenu(event, markdown) {
    if (!menu) {
      return;
    }
    activeMarkdown = markdown;
    menu.hidden = false;
    const width = menu.offsetWidth || 178;
    const height = menu.offsetHeight || 76;
    const left = Math.min(event.clientX, window.innerWidth - width - 8);
    const top = Math.min(event.clientY, window.innerHeight - height - 8);
    menu.style.left = Math.max(8, left) + "px";
    menu.style.top = Math.max(8, top) + "px";
  }

  document.addEventListener("contextmenu", function (event) {
    const range = selectionRange();
    const markdown = range ? buildMarkdown(range) : "";
    if (!markdown) {
      hideMenu();
      return;
    }
    event.preventDefault();
    showMenu(event, markdown);
  });

  document.addEventListener("selectionchange", function () {
    if (!selectionRange()) {
      hideMenu();
    }
  });
  document.addEventListener("click", function (event) {
    if (menu && menu.contains(event.target)) {
      return;
    }
    hideMenu();
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      hideMenu();
    }
  });
  window.addEventListener("scroll", hideMenu, { passive: true });
  window.addEventListener("resize", hideMenu);

  if (plainAction) {
    plainAction.addEventListener("click", function () {
      copyPlainSelection();
    });
  }
  if (action) {
    action.addEventListener("click", function () {
      const markdown = activeMarkdown;
      hideMenu();
      copyMarkdown(markdown);
    });
  }
}());
</script>
"""


def diagram_script() -> str:
    return """<script>
(function () {
  const modal = document.getElementById("diagram-modal");
  if (!modal) {
    return;
  }
  const title = document.getElementById("diagram-modal-title");
  const content = document.getElementById("diagram-modal-content");
  const zoomLabel = document.getElementById("diagram-zoom-label");
  const searchInput = document.getElementById("diagram-search");
  const searchCount = document.getElementById("diagram-search-count");
  const generalViewButton = document.getElementById("diagram-general-view");
  const storyContext = document.getElementById("diagram-story-context");
  const storyTitle = document.getElementById("diagram-story-title");
  const storyBody = document.getElementById("diagram-story-body");
  const zoomTools = Array.from(document.querySelectorAll("[data-diagram-zoom-tool]"));
  let scale = 1;
  let initialScale = 1;
  let mode = "";
  let activeFocusTerms = [];
  let activeNotes = [];
  let activeCodeLinks = [];
  let activeCodeLinkHoverInstance = "";
  let activeCodeLinkHoverTarget = "";
  let searchMatches = [];
  let searchIndex = -1;
  let isPanning = false;
  let panStartX = 0;
  let panStartY = 0;
  let panStartLeft = 0;
  let panStartTop = 0;

  function setScale(nextScale) {
    scale = Math.max(0.25, Math.min(4, nextScale));
    if (zoomLabel) {
      zoomLabel.textContent = Math.round(scale * 100) + "%";
    }
    const stage = content.querySelector(".diagram-zoom-stage");
    if (stage) {
      stage.style.transform = "scale(" + scale + ")";
      stage.style.marginRight = ((scale - 1) * stage.scrollWidth) + "px";
      stage.style.marginBottom = ((scale - 1) * stage.scrollHeight) + "px";
    }
  }

  function setInitialDiagramScale() {
    initialScale = 1;
    if (mode !== "diagram") {
      setScale(initialScale);
      return;
    }
    const svg = content.querySelector(".diagram-zoom-stage svg");
    const size = svgNaturalSize(svg);
    if (!size || !size.width || !size.height) {
      setScale(initialScale);
      return;
    }
    const availableWidth = Math.max(0, content.clientWidth - 36);
    const availableHeight = Math.max(0, content.clientHeight - 36);
    if (size.width > availableWidth || size.height > availableHeight) {
      setScale(initialScale);
      return;
    }
    initialScale = Math.min(3, availableWidth / size.width, availableHeight / size.height);
    setScale(initialScale);
  }

  function svgNaturalSize(svg) {
    if (!svg) {
      return null;
    }
    if (svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width && svg.viewBox.baseVal.height) {
      return {
        width: svg.viewBox.baseVal.width,
        height: svg.viewBox.baseVal.height,
      };
    }
    let box;
    try {
      box = svg.getBBox();
    } catch (error) {
      return null;
    }
    return box ? { width: box.width, height: box.height } : null;
  }

  function setMode(nextMode) {
    mode = nextMode;
    content.dataset.mode = mode;
    for (const tool of zoomTools) {
      tool.hidden = mode !== "diagram";
    }
  }

  function clearSearch() {
    searchMatches = [];
    searchIndex = -1;
    if (searchCount) {
      searchCount.textContent = "";
    }
    if (mode === "log") {
      renderLogView("", activeFocusTerms);
      return;
    }
    for (const node of content.querySelectorAll(".asset-search-match, .asset-search-current")) {
      node.classList.remove("asset-search-match", "asset-search-current");
    }
  }

  function clearFocus() {
    activeFocusTerms = [];
    activeNotes = [];
    for (const node of content.querySelectorAll(".diagram-note-layer")) {
      node.remove();
    }
    for (const node of content.querySelectorAll(".asset-focus-connector")) {
      node.classList.remove("asset-focus-connector", "asset-focus-connector-reverse");
    }
    for (const node of content.querySelectorAll(".asset-focus-match")) {
      node.classList.remove("asset-focus-match", "asset-focus-related-hover");
    }
    for (const node of content.querySelectorAll(".asset-focus-related-hover")) {
      node.classList.remove("asset-focus-related-hover");
    }
    for (const node of content.querySelectorAll(".diagram-code-link-hover")) {
      node.classList.remove("diagram-code-link-hover");
    }
    activeCodeLinkHoverInstance = "";
    activeCodeLinkHoverTarget = "";
    if (mode === "log") {
      renderLogView(searchInput ? searchInput.value : "", activeFocusTerms);
    }
    if (generalViewButton) {
      generalViewButton.hidden = true;
    }
  }

  function parseFocus(value) {
    if (!value) {
      return [];
    }
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) {
        return parsed.map(String).filter(Boolean);
      }
    } catch (error) {
      return [String(value)];
    }
    return [String(value)];
  }

  function matchesAnyTerm(text, terms) {
    const lowerText = text.toLowerCase();
    return terms.some(function (term) {
      return lowerText.includes(String(term).toLowerCase());
    });
  }

  function markSvgFocusMatch(node) {
    const labelNode = svgTextLabelNode(node);
    labelNode.classList.add("asset-focus-match");
    if (labelNode.querySelectorAll) {
      for (const child of labelNode.querySelectorAll("tspan")) {
        child.classList.add("asset-focus-match");
      }
    }
  }

  function svgLabelLineGroup(node) {
    const labelNode = svgTextLabelNode(node);
    const box = safeBBox(labelNode);
    const parent = labelNode.parentNode;
    if (!box || !parent || !labelNode.tagName || labelNode.tagName.toLowerCase() !== "text") {
      return [labelNode];
    }
    const group = [];
    const x = Number.parseFloat(labelNode.getAttribute("x") || "");
    const centerY = box.y + box.height / 2;
    for (const candidate of parent.querySelectorAll("text")) {
      const candidateBox = safeBBox(candidate);
      if (!candidateBox) {
        continue;
      }
      const candidateX = Number.parseFloat(candidate.getAttribute("x") || "");
      const candidateCenterY = candidateBox.y + candidateBox.height / 2;
      if (
        Number.isFinite(x)
        && Number.isFinite(candidateX)
        && Math.abs(candidateX - x) <= 2
        && Math.abs(candidateCenterY - centerY) <= 22
      ) {
        group.push(candidate);
      }
    }
    return group.length ? group : [labelNode];
  }

  function isSvgConnector(node) {
    if (!node || !node.tagName) {
      return false;
    }
    const tag = node.tagName.toLowerCase();
    return tag === "line" || tag === "polyline" || tag === "polygon" || tag === "path";
  }

  function addSvgFocusConnector(node) {
    const connectors = connectorsForText(node);
    const arrowhead = connectors.find(function (connector) {
      return connector.tagName && connector.tagName.toLowerCase() === "polygon";
    });
    for (const connector of connectors) {
      connector.classList.add("asset-focus-connector");
      if (isReverseConnector(connector, arrowhead)) {
        connector.classList.add("asset-focus-connector-reverse");
      }
    }
  }

  function connectorsForText(node) {
    let current = node.previousElementSibling;
    let inspected = 0;
    const connectors = [];
    while (current && inspected < 5 && connectors.length < 2) {
      if (isSvgConnector(current)) {
        connectors.push(current);
      }
      current = current.previousElementSibling;
      inspected += 1;
    }
    return connectors;
  }

  function isReverseConnector(node, arrowhead) {
    const tag = node.tagName.toLowerCase();
    const points = connectorEndpoints(node, tag);
    if (!points) {
      return false;
    }
    if (arrowhead && node !== arrowhead) {
      const arrowCenter = connectorCenter(arrowhead, "polygon");
      if (arrowCenter) {
        const startDistance = distance(points.start, arrowCenter);
        const endDistance = distance(points.end, arrowCenter);
        return startDistance < endDistance;
      }
    }
    const dx = points.end.x - points.start.x;
    const dy = points.end.y - points.start.y;
    if (Math.abs(dx) >= Math.abs(dy)) {
      return dx < 0;
    }
    return dy < 0;
  }

  function connectorEndpoints(node, tag) {
    if (tag === "line") {
      return {
        start: { x: numberAttr(node, "x1"), y: numberAttr(node, "y1") },
        end: { x: numberAttr(node, "x2"), y: numberAttr(node, "y2") },
      };
    }
    if (tag === "polyline" || tag === "polygon") {
      return endpointsFromNumbers((node.getAttribute("points") || "").match(/-?\\d+(?:\\.\\d+)?/g));
    }
    if (tag === "path") {
      return endpointsFromNumbers((node.getAttribute("d") || "").match(/-?\\d+(?:\\.\\d+)?/g));
    }
    return null;
  }

  function endpointsFromNumbers(rawNumbers) {
    if (!rawNumbers || rawNumbers.length < 4) {
      return null;
    }
    const numbers = rawNumbers.map(Number);
    return {
      start: { x: numbers[0], y: numbers[1] },
      end: { x: numbers[numbers.length - 2], y: numbers[numbers.length - 1] },
    };
  }

  function connectorCenter(node, tag) {
    const endpoints = connectorEndpoints(node, tag);
    if (!endpoints) {
      return null;
    }
    return {
      x: (endpoints.start.x + endpoints.end.x) / 2,
      y: (endpoints.start.y + endpoints.end.y) / 2,
    };
  }

  function distance(a, b) {
    const dx = a.x - b.x;
    const dy = a.y - b.y;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function numberAttr(node, name) {
    return Number(node.getAttribute(name) || 0);
  }

  function updateSearch(resetIndex) {
    clearSearch();
    const query = searchInput ? searchInput.value : "";
    if (!query) {
      return;
    }
    if (mode === "diagram") {
      searchDiagram(query);
    } else if (mode === "log") {
      searchLog(query);
    }
    if (!searchMatches.length) {
      if (searchCount) {
        searchCount.textContent = "0";
      }
      return;
    }
    searchIndex = resetIndex ? 0 : Math.max(0, Math.min(searchIndex, searchMatches.length - 1));
    showSearchMatch();
  }

  function searchDiagram(query) {
    const lowerQuery = query.toLowerCase();
    const textNodes = content.querySelectorAll("svg text");
    for (const node of textNodes) {
      if (node.textContent.toLowerCase().includes(lowerQuery)) {
        node.classList.add("asset-search-match");
        searchMatches.push(node);
      }
    }
  }

  function searchLog(query) {
    renderLogView(query, activeFocusTerms);
  }

  function appendSearchParts(parent, text, query) {
    if (!query) {
      parent.appendChild(document.createTextNode(text));
      return;
    }
    const lowerText = text.toLowerCase();
    const lowerQuery = query.toLowerCase();
    let offset = 0;
    while (true) {
      const matchAt = lowerText.indexOf(lowerQuery, offset);
      if (matchAt === -1) {
        break;
      }
      parent.appendChild(document.createTextNode(text.slice(offset, matchAt)));
      const mark = document.createElement("mark");
      mark.className = "asset-search-match";
      mark.textContent = text.slice(matchAt, matchAt + query.length);
      parent.appendChild(mark);
      searchMatches.push(mark);
      offset = matchAt + query.length;
    }
    parent.appendChild(document.createTextNode(text.slice(offset)));
  }

  function renderLogView(query, focusTerms) {
    const pre = content.querySelector(".log-view-text");
    if (!pre) {
      return;
    }
    const sourceText = pre.dataset.sourceText || pre.textContent;
    pre.dataset.sourceText = sourceText;
    const fragment = document.createDocumentFragment();
    const lines = sourceText.split("\\n");
    lines.forEach(function (line, index) {
      if (matchesAnyTerm(line, focusTerms)) {
        const span = document.createElement("span");
        span.className = "asset-focus-line";
        appendSearchParts(span, line, query);
        fragment.appendChild(span);
      } else {
        appendSearchParts(fragment, line, query);
      }
      if (index < lines.length - 1) {
        fragment.appendChild(document.createTextNode("\\n"));
      }
    });
    pre.replaceChildren(fragment);
  }

  function parseNotes(value) {
    if (!value) {
      return [];
    }
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function parseCodeLinks(value) {
    if (!value) {
      return [];
    }
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function applyFocusTerms(terms, notes) {
    clearFocus();
    activeFocusTerms = terms;
    activeNotes = notes || [];
    if (generalViewButton) {
      generalViewButton.hidden = !(activeFocusTerms.length || activeNotes.length);
    }
    if (mode === "diagram") {
      const focused = [];
      const textNodes = content.querySelectorAll("svg text, svg tspan");
      const focusedLabels = new Set();
      for (const node of textNodes) {
        if (matchesAnyTerm(node.textContent, activeFocusTerms)) {
          const labelNode = svgTextLabelNode(node);
          if (focusedLabels.has(labelNode)) {
            continue;
          }
          const labelLines = svgLabelLineGroup(labelNode);
          for (const labelLine of labelLines) {
            focusedLabels.add(labelLine);
            markSvgFocusMatch(labelLine);
          }
          addSvgFocusConnector(labelNode);
          focused.push(labelNode);
        }
      }
      addDiagramNotes(notes || [], textNodes);
      if (focused[0]) {
        window.setTimeout(function () {
          animateScrollContainerToElement(content, focused[0], 1000);
        }, 40);
      }
    } else if (mode === "log") {
      renderLogView(searchInput ? searchInput.value : "", activeFocusTerms);
      const firstLine = content.querySelector(".asset-focus-line");
      if (firstLine) {
        window.setTimeout(function () {
          animateScrollContainerToElement(content, firstLine, 1000, { horizontal: false });
        }, 40);
      }
    }
  }

  function animateScrollContainerToElement(container, element, durationMs, options) {
    const scrollHorizontal = !options || options.horizontal !== false;
    const startLeft = container.scrollLeft;
    const startTop = container.scrollTop;
    const containerRect = container.getBoundingClientRect();
    const targetRect = elementViewportRect(element);
    const maxLeft = Math.max(0, container.scrollWidth - container.clientWidth);
    const maxTop = Math.max(0, container.scrollHeight - container.clientHeight);
    const targetLeft = scrollHorizontal
      ? clamp(
          startLeft + targetRect.left - containerRect.left - container.clientWidth / 2 + targetRect.width / 2,
          0,
          maxLeft
        )
      : startLeft;
    const targetTop = clamp(
      startTop + targetRect.top - containerRect.top - container.clientHeight / 2 + targetRect.height / 2,
      0,
      maxTop
    );
    const deltaLeft = targetLeft - startLeft;
    const deltaTop = targetTop - startTop;
    const startedAt = performance.now();
    if (!deltaLeft && !deltaTop) {
      return;
    }
    function tick(now) {
      const elapsed = Math.min(1, (now - startedAt) / durationMs);
      const eased = elapsed < 0.5
        ? 4 * elapsed * elapsed * elapsed
        : 1 - Math.pow(-2 * elapsed + 2, 3) / 2;
      container.scrollLeft = startLeft + deltaLeft * eased;
      container.scrollTop = startTop + deltaTop * eased;
      if (elapsed < 1) {
        window.setTimeout(function () {
          tick(performance.now());
        }, 16);
      }
    }
    tick(performance.now());
    window.setTimeout(function () {
      container.scrollLeft = targetLeft;
      container.scrollTop = targetTop;
    }, durationMs + 30);
  }

  function elementViewportRect(element) {
    if (element.ownerSVGElement && typeof element.getBBox === "function") {
      const svgRect = svgElementViewportRect(element);
      if (svgRect) {
        return svgRect;
      }
    }
    return element.getBoundingClientRect();
  }

  function svgElementViewportRect(element) {
    let box;
    let matrix;
    try {
      box = element.getBBox();
      matrix = element.getScreenCTM();
    } catch (error) {
      return null;
    }
    if (!box || !matrix) {
      return null;
    }
    const points = [
      svgPoint(element, box.x, box.y).matrixTransform(matrix),
      svgPoint(element, box.x + box.width, box.y).matrixTransform(matrix),
      svgPoint(element, box.x, box.y + box.height).matrixTransform(matrix),
      svgPoint(element, box.x + box.width, box.y + box.height).matrixTransform(matrix),
    ];
    const xs = points.map(function (point) { return point.x; });
    const ys = points.map(function (point) { return point.y; });
    const left = Math.min.apply(Math, xs);
    const top = Math.min.apply(Math, ys);
    const right = Math.max.apply(Math, xs);
    const bottom = Math.max.apply(Math, ys);
    return {
      left,
      top,
      width: right - left,
      height: bottom - top,
    };
  }

  function svgPoint(element, x, y) {
    const svg = element.ownerSVGElement;
    if (svg && typeof svg.createSVGPoint === "function") {
      const point = svg.createSVGPoint();
      point.x = x;
      point.y = y;
      return point;
    }
    return new DOMPoint(x, y);
  }

  function applyCodeLinks(links) {
    activeCodeLinks = links || [];
    closeCodePopover();
    activeCodeLinkHoverInstance = "";
    activeCodeLinkHoverTarget = "";
    for (const node of content.querySelectorAll(".diagram-code-link-badge")) {
      node.remove();
    }
    for (const node of content.querySelectorAll(".diagram-code-link-target, .diagram-code-link-connector, .diagram-code-link-hover, .diagram-code-link-active")) {
      node.classList.remove("diagram-code-link-target", "diagram-code-link-connector", "diagram-code-link-hover", "diagram-code-link-active");
      delete node.dataset.codeLinkTarget;
      delete node.dataset.codeLinkInstance;
    }
    if (mode !== "diagram" || !activeCodeLinks.length) {
      return;
    }
    const textNodes = content.querySelectorAll("svg text, svg tspan");
    let instanceIndex = 0;
    for (const link of activeCodeLinks) {
      const target = String(link.target || "").toLowerCase();
      if (!target) {
        continue;
      }
      const linkedLabels = new Set();
      for (const node of textNodes) {
        if (!node.textContent.toLowerCase().includes(target)) {
          continue;
        }
        const labelNode = svgTextLabelNode(node);
        if (linkedLabels.has(labelNode)) {
          continue;
        }
        linkedLabels.add(labelNode);
        decorateCodeLinkTarget(labelNode, link, "code-link-" + String(instanceIndex));
        instanceIndex += 1;
      }
    }
  }

  function decorateCodeLinkTarget(node, link, instanceKey) {
    node = svgTextLabelNode(node);
    const targetKey = String(link.target || "");
    const connectors = connectorsForText(node);
    node.classList.add("diagram-code-link-target");
    node.dataset.codeLinkTarget = targetKey;
    node.dataset.codeLinkInstance = instanceKey;
    attachCodeLinkHover(node, targetKey, instanceKey);
    for (const connector of connectors) {
      connector.classList.add("diagram-code-link-connector");
      connector.dataset.codeLinkTarget = targetKey;
      connector.dataset.codeLinkInstance = instanceKey;
      attachCodeLinkHover(connector, targetKey, instanceKey);
    }
    addCodeLinkBadge(node, targetKey, instanceKey);
  }

  function svgTextLabelNode(node) {
    if (node && node.tagName && node.tagName.toLowerCase() === "tspan" && node.parentElement) {
      return node.parentElement;
    }
    return node;
  }

  function attachCodeLinkHover(node, targetKey, instanceKey) {
    node.dataset.codeLinkTarget = targetKey;
    node.dataset.codeLinkInstance = instanceKey;
  }

  function setCodeLinkHover(targetKey, instanceKey, enabled) {
    for (const node of content.querySelectorAll("[data-code-link-instance]")) {
      if (node.dataset.codeLinkInstance === instanceKey) {
        node.classList.toggle(
          "diagram-code-link-hover",
          enabled && node.classList.contains("diagram-code-link-badge")
        );
      }
    }
    setDiagramNoteHoverForTarget(targetKey, enabled);
  }

  function updateCodeLinkHoverFromPointer(event) {
    if (modal.hidden || mode !== "diagram") {
      clearCodeLinkHover();
      return;
    }
    const pointerTarget = document.elementFromPoint(event.clientX, event.clientY);
    const item = pointerTarget ? pointerTarget.closest(".diagram-code-link-badge") : null;
    if (!item || !content.contains(item)) {
      clearCodeLinkHover();
      return;
    }
    const instanceKey = item.dataset.codeLinkInstance || "";
    const targetKey = item.dataset.codeLinkTarget || "";
    if (!instanceKey || instanceKey === activeCodeLinkHoverInstance) {
      return;
    }
    clearCodeLinkHover();
    activeCodeLinkHoverInstance = instanceKey;
    activeCodeLinkHoverTarget = targetKey;
    setCodeLinkHover(targetKey, instanceKey, true);
  }

  function clearCodeLinkHover() {
    if (!activeCodeLinkHoverInstance) {
      return;
    }
    setCodeLinkHover(activeCodeLinkHoverTarget, activeCodeLinkHoverInstance, false);
    activeCodeLinkHoverInstance = "";
    activeCodeLinkHoverTarget = "";
  }

  function setDiagramNoteHoverForTarget(targetKey, enabled) {
    const normalizedTarget = String(targetKey || "").toLowerCase();
    if (!normalizedTarget) {
      return;
    }
    for (const note of content.querySelectorAll("[data-diagram-note-target]")) {
      const noteTarget = String(note.dataset.diagramNoteTarget || "").toLowerCase();
      if (noteTarget && (normalizedTarget.includes(noteTarget) || noteTarget.includes(normalizedTarget))) {
        note.classList.toggle("diagram-note-hover", enabled);
      }
    }
  }

  function addCodeLinkBadge(labelNode, targetKey, instanceKey) {
    const svg = labelNode.ownerSVGElement;
    const box = safeBBox(labelNode);
    if (!svg || !box) {
      return;
    }
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.setAttribute("class", "diagram-code-link-badge");
    group.dataset.codeLinkTarget = targetKey;
    group.dataset.codeLinkInstance = instanceKey;
    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = "Open linked diff code";
    group.appendChild(title);
    const badge = codeLinkBadgePlacement(svg, box);
    const x = badge.x;
    const y = badge.y;
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("class", "diagram-code-link-badge-box");
    rect.setAttribute("x", String(x));
    rect.setAttribute("y", String(y));
    rect.setAttribute("width", "28");
    rect.setAttribute("height", "18");
    group.appendChild(rect);
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("class", "diagram-code-link-badge-text");
    text.setAttribute("x", String(x + 14));
    text.setAttribute("y", String(y + 9));
    text.textContent = "C";
    group.appendChild(text);
    group.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      activateCodeLink(targetKey, instanceKey);
    });
    attachCodeLinkHover(group, targetKey, instanceKey);
    const parent = labelNode.parentNode || svg;
    parent.appendChild(group);
  }

  function codeLinkBadgePlacement(svg, labelBox) {
    const width = 28;
    const height = 18;
    const gap = 8;
    const candidates = [
      { x: labelBox.x + labelBox.width + gap, y: labelBox.y + labelBox.height / 2 - height / 2 },
      { x: labelBox.x - width - gap, y: labelBox.y + labelBox.height / 2 - height / 2 },
      { x: labelBox.x + labelBox.width + gap, y: labelBox.y + labelBox.height + gap },
      { x: labelBox.x + labelBox.width + gap, y: labelBox.y - height - gap },
    ];
    const occupied = nearbyDiagramNoteBoxes(svg);
    for (const candidate of candidates) {
      const candidateBox = { x: candidate.x - 3, y: candidate.y - 3, width: width + 6, height: height + 6 };
      if (!occupied.some(function (box) { return svgBoxesOverlap(candidateBox, box); })) {
        return candidate;
      }
    }
    return candidates[1];
  }

  function nearbyDiagramNoteBoxes(svg) {
    const boxes = [];
    for (const node of svg.querySelectorAll(".diagram-note-hotspot")) {
      const box = safeBBox(node);
      if (box) {
        boxes.push({ x: box.x - 4, y: box.y - 4, width: box.width + 8, height: box.height + 8 });
      }
    }
    return boxes;
  }

  function svgBoxesOverlap(a, b) {
    return a.x < b.x + b.width
      && a.x + a.width > b.x
      && a.y < b.y + b.height
      && a.y + a.height > b.y;
  }

  function activateCodeLink(targetKey, instanceKey) {
    const links = activeCodeLinks.filter(function (link) {
      return String(link.target || "") === String(targetKey || "");
    });
    if (!links.length) {
      return;
    }
    markActiveCodeLink(instanceKey);
    renderCodePopover(targetKey, links);
  }

  function markActiveCodeLink(instanceKey) {
    for (const node of content.querySelectorAll(".diagram-code-link-active")) {
      node.classList.remove("diagram-code-link-active");
    }
    for (const node of content.querySelectorAll("[data-code-link-instance]")) {
      if (node.dataset.codeLinkInstance === instanceKey) {
        node.classList.add("diagram-code-link-active");
      }
    }
  }

  function codeOverlayRoot() {
    return document.body;
  }

  function closeCodePopover() {
    const overlay = codeOverlayRoot().querySelector(".diagram-code-overlay");
    if (overlay) {
      overlay.remove();
    }
    for (const node of content.querySelectorAll(".diagram-code-link-active")) {
      node.classList.remove("diagram-code-link-active");
    }
    for (const node of content.querySelectorAll(".diagram-code-link-hover")) {
      node.classList.remove("diagram-code-link-hover");
    }
    activeCodeLinkHoverInstance = "";
    activeCodeLinkHoverTarget = "";
  }

  function renderCodePopover(targetKey, links) {
    closeExistingCodePopoverOnly();
    const overlay = document.createElement("div");
    overlay.className = "diagram-code-overlay";
    overlay.addEventListener("click", function (event) {
      if (event.target === overlay) {
        closeCodePopover();
      }
    });
    const popover = document.createElement("section");
    popover.className = "diagram-code-popover";
    popover.setAttribute("aria-label", "Code linked from diagram");
    popover.addEventListener("click", function (event) {
      event.stopPropagation();
    });
    const header = document.createElement("div");
    header.className = "diagram-code-popover-header";
    const heading = document.createElement("span");
    heading.className = "diagram-code-popover-title";
    const headingTitle = document.createElement("span");
    headingTitle.textContent = targetKey;
    heading.appendChild(headingTitle);
    const headingFile = document.createElement("span");
    headingFile.className = "diagram-code-popover-file";
    headingFile.textContent = codePopoverLocation(links);
    heading.appendChild(headingFile);
    header.appendChild(heading);
    const close = document.createElement("button");
    close.type = "button";
    close.className = "diagram-code-popover-close";
    close.setAttribute("aria-label", "Close linked code");
    close.textContent = "×";
    close.addEventListener("click", closeCodePopover);
    header.appendChild(close);
    popover.appendChild(header);
    const body = document.createElement("div");
    body.className = "diagram-code-popover-body";
    for (const link of links) {
      body.appendChild(createCodeLinkItem(link));
    }
    popover.appendChild(body);
    overlay.appendChild(popover);
    codeOverlayRoot().appendChild(overlay);
    positionCodePopover(popover);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        positionCodePopover(popover);
        centerCodeTarget(popover);
      });
    });
  }

  function positionCodePopover(popover) {
    const dialog = modal.querySelector(".diagram-dialog");
    const rect = dialog ? dialog.getBoundingClientRect() : modal.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    popover.style.left = centerX + "px";
    popover.style.top = centerY + "px";
    popover.style.maxWidth = Math.max(320, rect.width - 64) + "px";
    popover.style.maxHeight = Math.max(320, rect.height - 64) + "px";
  }

  function codePopoverLocation(links) {
    const first = links && links[0] ? links[0] : {};
    const file = String(first.file || "unknown file");
    return file.split("/").filter(Boolean).pop() || file;
  }

  function centerCodeTarget(popover) {
    const firstTarget = popover.querySelector(".diagram-code-target-line");
    if (!firstTarget) {
      return;
    }
    const scroller = popover.querySelector(".diagram-code-popover-body");
    if (!scroller) {
      return;
    }
    const scrollerRect = scroller.getBoundingClientRect();
    const targetRect = firstTarget.getBoundingClientRect();
    const targetMiddle = (
      scroller.scrollTop
      + targetRect.top
      - scrollerRect.top
      + targetRect.height / 2
    );
    const maxScroll = Math.max(0, scroller.scrollHeight - scroller.clientHeight);
    scroller.scrollTop = Math.min(maxScroll, Math.max(0, targetMiddle - scroller.clientHeight / 2));
  }

  function closeExistingCodePopoverOnly() {
    const overlay = codeOverlayRoot().querySelector(".diagram-code-overlay");
    if (overlay) {
      overlay.remove();
    }
  }

  function createCodeLinkItem(link) {
    const item = document.createElement("div");
    item.className = "diagram-code-link-item";
    const titleNode = document.createElement("span");
    titleNode.className = "diagram-code-link-title";
    titleNode.textContent = String(link.title || link.target || "Code");
    item.appendChild(titleNode);
    const location = document.createElement("span");
    location.className = "diagram-code-link-location";
    location.textContent = String(link.file || "") + ":" + String(link.line || "");
    item.appendChild(location);
    const code = document.createElement("code");
    code.className = "diagram-code-link-code";
    renderDiffFileContext(code, link);
    item.appendChild(code);
    return item;
  }

  function renderDiffFileContext(parent, link) {
    const rows = diffFileRowsForLink(link);
    if (!rows.length) {
      parent.textContent = "Target file is not present in this rendered diff.";
      return;
    }
    const targetRange = targetRangeForLink(link);
    const targetLine = Number(link.line);
    rows.forEach(function (row, index) {
      const line = Number(row.dataset.newLine || 0);
      const span = document.createElement("span");
      span.className = "diagram-code-line";
      if (targetRange && line >= targetRange.start && line <= targetRange.end) {
        span.classList.add("diagram-code-context-line");
      }
      if (Number.isFinite(targetLine) && line === targetLine) {
        span.classList.add("diagram-code-target-line");
      }
      const newLine = row.dataset.newLine || "";
      const code = row.querySelector(".code");
      span.textContent = String(newLine).padStart(5, " ") + "  " + (code ? code.textContent : "");
      parent.appendChild(span);
    });
  }

  function diffFileRowsForLink(link) {
    const filePath = String(link.file || "");
    if (!filePath) {
      return [];
    }
    return Array.from(document.querySelectorAll("tr[data-file]")).filter(function (row) {
      return row.dataset.file === filePath && row.dataset.newLine;
    });
  }

  function targetRangeForLink(link) {
    const filePath = String(link.file || "");
    const startLine = Number((link.range && link.range.start) || link.line);
    const endLine = Number((link.range && link.range.end) || link.line);
    if (!filePath || !Number.isFinite(startLine) || !Number.isFinite(endLine)) {
      return null;
    }
    return { start: Math.min(startLine, endLine), end: Math.max(startLine, endLine) };
  }

  function isDiagramNoteTarget(node, notes) {
    return notes.some(function (note) {
      const target = String(note.target || "").toLowerCase();
      return target && node.textContent.toLowerCase().includes(target);
    });
  }

  function addDiagramNotes(notes, textNodes) {
    if (!notes.length) {
      return;
    }
    const svg = content.querySelector("svg");
    if (!svg) {
      return;
    }
    const layer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    layer.setAttribute("class", "diagram-note-layer");
    svg.appendChild(layer);
    const viewBox = svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width
      ? svg.viewBox.baseVal
      : { x: 0, y: 0, width: Number(svg.getAttribute("width")) || 900, height: Number(svg.getAttribute("height")) || 900 };
    notes.forEach(function (note, index) {
      const target = findNoteTarget(textNodes, note.target || "");
      if (!target) {
        return;
      }
      const targetBox = safeBBox(target);
      if (!targetBox) {
        return;
      }
      const noteWidth = Math.min(320, Math.max(180, String(note.text || "").length * 4.2 + 24));
      const noteLines = estimateSvgTextLines(String(note.text || ""), noteWidth - 20);
      const noteHeight = Math.max(44, 18 + noteLines * 15);
      const connectors = connectorsForText(target);
      const anchor = labelRightAnchor(targetBox);
      const marker = diagramNoteMarkerPosition(viewBox, anchor);
      const position = diagramNotePosition(note, viewBox, marker, noteWidth, noteHeight, index);
      const x = position.x;
      const y = position.y;
      const group = createDiagramNote(note, x, y, noteWidth, noteHeight, marker, connectors.concat([target]));
      layer.appendChild(group);
      raiseFocusTarget(target, connectors);
    });
  }

  function diagramNoteMarkerPosition(viewBox, anchor) {
    const margin = 18;
    return {
      x: clamp(anchor.x + 18, viewBox.x + margin, viewBox.x + viewBox.width - margin),
      y: clamp(anchor.y, viewBox.y + margin, viewBox.y + viewBox.height - margin),
    };
  }

  function diagramNotePosition(note, viewBox, marker, width, height, index) {
    const margin = 24;
    const maxXOffset = 360;
    const maxYOffset = 220;
    const minX = viewBox.x + margin;
    const maxX = viewBox.x + viewBox.width - width - margin;
    const minY = viewBox.y + margin;
    const maxY = viewBox.y + viewBox.height - height - margin;
    if (Number.isFinite(note.x) && Number.isFinite(note.y)) {
      return {
        x: clamp(Number(note.x), minX, maxX),
        y: clamp(Number(note.y), minY, maxY),
      };
    }
    const rightX = clamp(marker.x + 30, minX, Math.min(maxX, marker.x + maxXOffset));
    const leftX = clamp(marker.x - width - 30, Math.max(minX, marker.x - maxXOffset), maxX);
    const hasRoomRight = rightX >= marker.x + 18;
    const x = hasRoomRight ? rightX : leftX;
    const idealY = marker.y - height / 2 + index * 4;
    const y = clamp(idealY, Math.max(minY, marker.y - maxYOffset), Math.min(maxY, marker.y + maxYOffset));
    return { x, y };
  }

  function clamp(value, min, max) {
    if (max < min) {
      return min;
    }
    return Math.min(max, Math.max(min, value));
  }

  function findNoteTarget(textNodes, targetText) {
    const targets = normalizedDiagramNoteTargets(targetText);
    const seenLabels = new Set();
    for (const node of textNodes) {
      const labelNode = svgTextLabelNode(node);
      if (seenLabels.has(labelNode)) {
        continue;
      }
      seenLabels.add(labelNode);
      const labelText = labelNode.textContent.toLowerCase();
      if (targets.some(function (target) { return labelText.includes(target); })) {
        return labelNode;
      }
    }
    return null;
  }

  function normalizedDiagramNoteTargets(targetText) {
    const rawTarget = String(targetText || "").toLowerCase().trim();
    const targets = rawTarget ? [rawTarget] : [];
    const colonIndex = rawTarget.lastIndexOf(":");
    if (colonIndex >= 0) {
      const labelOnly = rawTarget.slice(colonIndex + 1).trim();
      if (labelOnly) {
        targets.push(labelOnly);
      }
    }
    return targets;
  }

  function labelRightAnchor(box) {
    return {
      x: box.x + box.width + 6,
      y: box.y + box.height / 2,
    };
  }

  function createDiagramNote(note, x, y, width, height, markerPoint, relatedNodes) {
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.setAttribute("class", "diagram-note-hotspot");
    group.dataset.diagramNoteTarget = String(note.target || "");
    for (const eventName of ["click", "dblclick", "mousedown", "pointerdown"]) {
      group.addEventListener(eventName, stopDiagramNoteEvent);
    }
    const markerX = markerPoint.x;
    const markerY = markerPoint.y;
    const marker = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    marker.setAttribute("class", "diagram-note-marker");
    marker.setAttribute("cx", String(markerX));
    marker.setAttribute("cy", String(markerY));
    marker.setAttribute("r", "9");
    group.appendChild(marker);
    const markerText = document.createElementNS("http://www.w3.org/2000/svg", "text");
    markerText.setAttribute("class", "diagram-note-marker-text");
    markerText.setAttribute("x", String(markerX));
    markerText.setAttribute("y", String(markerY + 0.5));
    markerText.textContent = "i";
    group.appendChild(markerText);
    const panel = document.createElementNS("http://www.w3.org/2000/svg", "g");
    panel.setAttribute("class", "diagram-note-panel");
    const link = document.createElementNS("http://www.w3.org/2000/svg", "path");
    link.setAttribute("class", "diagram-note-link");
    link.setAttribute("d", noteLinkPath(markerX, markerY, x, y + height / 2));
    panel.appendChild(link);
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("class", "diagram-note-box");
    rect.setAttribute("x", String(x));
    rect.setAttribute("y", String(y));
    rect.setAttribute("width", String(width));
    rect.setAttribute("height", String(height));
    panel.appendChild(rect);
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("class", "diagram-note-text");
    text.setAttribute("x", String(x + 10));
    text.setAttribute("y", String(y + 18));
    wrapSvgText(text, String(note.text || ""), width - 20);
    panel.appendChild(text);
    group.appendChild(panel);
    group.addEventListener("mouseenter", function () {
      group.classList.add("diagram-note-hover");
      for (const node of relatedNodes) {
        node.classList.add("asset-focus-related-hover");
      }
    });
    group.addEventListener("mouseleave", function () {
      group.classList.remove("diagram-note-hover");
      for (const node of relatedNodes) {
        node.classList.remove("asset-focus-related-hover");
      }
    });
    for (const node of relatedNodes) {
      node.addEventListener("mouseenter", function () {
        group.classList.add("diagram-note-hover");
        for (const item of relatedNodes) {
          item.classList.add("asset-focus-related-hover");
        }
      });
      node.addEventListener("mouseleave", function () {
        group.classList.remove("diagram-note-hover");
        for (const item of relatedNodes) {
          item.classList.remove("asset-focus-related-hover");
        }
      });
    }
    return group;
  }

  function raiseFocusTarget(target, connectors) {
    const parent = target.parentNode;
    if (!parent) {
      return;
    }
    for (const connector of connectors) {
      if (connector.parentNode === parent) {
        parent.appendChild(connector);
      }
    }
    parent.appendChild(target);
  }

  function boxesOverlap(a, b) {
    return (
      a.x <= b.x + b.width &&
      a.x + a.width >= b.x &&
      a.y <= b.y + b.height &&
      a.y + a.height >= b.y
    );
  }

  function stopDiagramNoteEvent(event) {
    event.preventDefault();
    event.stopPropagation();
  }

  function noteLinkPath(x1, y1, x2, y2) {
    return [
      "M", x1, y1,
      "L", x2, y2,
    ].join(" ");
  }

  function estimateSvgTextLines(text, maxWidth) {
    const words = text.split(/\\s+/).filter(Boolean);
    let line = "";
    let lines = 0;
    for (const word of words) {
      const next = line ? line + " " + word : word;
      if (next.length * 6.4 > maxWidth && line) {
        lines += 1;
        line = word;
      } else {
        line = next;
      }
    }
    return lines + (line ? 1 : 0);
  }

  function wrapSvgText(textNode, text, maxWidth) {
    const words = text.split(/\\s+/);
    let line = "";
    let lineNo = 0;
    for (const word of words) {
      const next = line ? line + " " + word : word;
      if (next.length * 6.4 > maxWidth && line) {
        appendTspan(textNode, line, lineNo);
        line = word;
        lineNo += 1;
      } else {
        line = next;
      }
    }
    if (line) {
      appendTspan(textNode, line, lineNo);
    }
  }

  function appendTspan(textNode, text, lineNo) {
    const tspan = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
    tspan.setAttribute("x", textNode.getAttribute("x"));
    tspan.setAttribute("dy", lineNo === 0 ? "0" : "15");
    tspan.textContent = text;
    textNode.appendChild(tspan);
  }

  function safeBBox(node) {
    try {
      return node.getBBox();
    } catch (error) {
      return null;
    }
  }

  function showSearchMatch() {
    for (const node of searchMatches) {
      node.classList.remove("asset-search-current");
    }
    const current = searchMatches[searchIndex];
    if (!current) {
      return;
    }
    current.classList.add("asset-search-current");
    if (mode === "log") {
      animateScrollContainerToElement(content, current, 180, { horizontal: false });
    } else {
      current.scrollIntoView({ block: "center", inline: "center" });
    }
    if (searchCount) {
      searchCount.textContent = (searchIndex + 1) + "/" + searchMatches.length;
    }
  }

  function moveSearch(delta) {
    if (!searchMatches.length) {
      updateSearch(true);
      return;
    }
    searchIndex = (searchIndex + delta + searchMatches.length) % searchMatches.length;
    showSearchMatch();
  }

  function openTemplate(prefix, id, nextMode, focusTerms, notes, nextStoryContext) {
    const template = document.getElementById(prefix + "-template-" + id);
    if (!template) {
      return;
    }
    title.textContent = template.dataset.title || "Diagram";
    setStoryContext(nextStoryContext || null);
    content.innerHTML = "";
    const stage = document.createElement("div");
    stage.className = "diagram-zoom-stage";
    stage.appendChild(template.content.cloneNode(true));
    content.appendChild(stage);
    modal.hidden = false;
    document.body.style.overflow = "hidden";
    setMode(nextMode);
    if (searchInput) {
      searchInput.value = "";
    }
    setInitialDiagramScale();
    applyFocusTerms(focusTerms || [], notes || []);
    applyCodeLinks(nextMode === "diagram" ? parseCodeLinks(template.dataset.codeLinks) : []);
    if (nextMode === "log" && searchInput) {
      searchInput.focus();
    }
  }

  function setStoryContext(nextStoryContext) {
    const contextTitle = nextStoryContext ? String(nextStoryContext.title || "") : "";
    const contextBody = nextStoryContext ? String(nextStoryContext.body || "") : "";
    if (!storyContext || !storyTitle || !storyBody) {
      return;
    }
    storyTitle.textContent = contextTitle;
    storyBody.textContent = contextBody;
    storyContext.hidden = !(contextTitle || contextBody);
  }

  function storyContextFromTrigger(trigger) {
    const triggerTitle = trigger ? trigger.dataset.storyTitle || "" : "";
    const triggerBody = trigger ? trigger.dataset.storyBody || "" : "";
    return {
      title: triggerTitle || document.body.dataset.activeStoryTitle || "",
      body: triggerBody || document.body.dataset.activeStoryBody || "",
    };
  }

  function openDiagram(id, focusTerms, notes, nextStoryContext) {
    openTemplate("diagram", id, "diagram", focusTerms, notes, nextStoryContext);
  }

  function openLog(id, focusTerms, nextStoryContext) {
    openTemplate("log", id, "log", focusTerms, undefined, nextStoryContext);
  }

  function closeDiagram() {
    modal.hidden = true;
    content.innerHTML = "";
    document.body.style.overflow = "";
    scale = 1;
    initialScale = 1;
    setMode("");
    activeFocusTerms = [];
    activeNotes = [];
    activeCodeLinks = [];
    setStoryContext(null);
    closeCodePopover();
    clearSearch();
  }

  document.addEventListener("click", function (event) {
    const preview = event.target.closest("[data-diagram-id]");
    if (preview) {
      openDiagram(
        preview.dataset.diagramId,
        parseFocus(preview.dataset.diagramFocus),
        parseNotes(preview.dataset.diagramNotes),
        storyContextFromTrigger(preview)
      );
      return;
    }
    const logPreview = event.target.closest("[data-log-id]");
    if (logPreview) {
      openLog(
        logPreview.dataset.logId,
        parseFocus(logPreview.dataset.logFocus),
        storyContextFromTrigger(logPreview)
      );
      return;
    }
    if (event.target.closest("[data-diagram-close]")) {
      closeDiagram();
      return;
    }
    const zoom = event.target.closest("[data-diagram-zoom]");
    if (zoom) {
      const action = zoom.dataset.diagramZoom;
      if (action === "in") {
        setScale(scale + 0.25);
      } else if (action === "out") {
        setScale(scale - 0.25);
      } else {
        setScale(initialScale);
      }
      return;
    }
    const search = event.target.closest("[data-diagram-search]");
    if (search) {
      moveSearch(search.dataset.diagramSearch === "prev" ? -1 : 1);
      return;
    }
    if (event.target.closest("[data-diagram-general]")) {
      closeCodePopover();
      applyFocusTerms([], []);
      return;
    }
    if (event.target.closest(".diagram-code-popover")) {
      event.stopPropagation();
      return;
    }
  });

  document.addEventListener("keydown", function (event) {
    if (modal.hidden) {
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "f") {
      event.preventDefault();
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
      return;
    }
    if (event.key === "Enter" && document.activeElement === searchInput) {
      event.preventDefault();
      moveSearch(event.shiftKey ? -1 : 1);
      return;
    }
    if (event.key === "Escape") {
      if (codeOverlayRoot().querySelector(".diagram-code-overlay")) {
        closeCodePopover();
        return;
      }
      closeDiagram();
    }
  });

  document.addEventListener("pointermove", function (event) {
    updateCodeLinkHoverFromPointer(event);
  });

  document.addEventListener("pointerleave", function () {
    clearCodeLinkHover();
  });

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      clearCodeLinkHover();
    }
  });

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      updateSearch(true);
    });
  }

  content.addEventListener("wheel", function (event) {
    clearCodeLinkHover();
    if (!event.ctrlKey || modal.hidden || mode !== "diagram") {
      return;
    }
    event.preventDefault();
    const step = event.deltaY < 0 ? 0.1 : -0.1;
    setScale(scale + step);
  }, { passive: false });

  content.addEventListener("pointerdown", function (event) {
    if (modal.hidden || mode !== "diagram" || event.button !== 0) {
      return;
    }
    if (event.target.closest("button, input")) {
      return;
    }
    if (event.target.closest(".diagram-code-link-badge, .diagram-note-hotspot, .diagram-code-overlay")) {
      return;
    }
    clearCodeLinkHover();
    isPanning = true;
    panStartX = event.clientX;
    panStartY = event.clientY;
    panStartLeft = content.scrollLeft;
    panStartTop = content.scrollTop;
    content.classList.add("is-panning");
    content.setPointerCapture(event.pointerId);
    event.preventDefault();
  });

  content.addEventListener("pointermove", function (event) {
    if (!isPanning) {
      return;
    }
    content.scrollLeft = panStartLeft - (event.clientX - panStartX);
    content.scrollTop = panStartTop - (event.clientY - panStartY);
  });

  function stopPanning(event) {
    if (!isPanning) {
      return;
    }
    isPanning = false;
    content.classList.remove("is-panning");
    if (event && typeof event.pointerId === "number") {
      content.releasePointerCapture(event.pointerId);
    }
  }

  content.addEventListener("pointerup", stopPanning);
  content.addEventListener("pointercancel", stopPanning);
}());
</script>
"""



def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)

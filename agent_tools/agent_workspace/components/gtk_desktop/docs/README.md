# GTK Desktop Component

Owns the Linux-first GTK/VTE desktop frontend and GTK-only helpers.

Public callers import from `components.gtk_desktop.api`.

GTK is a frontend adapter. Business logic should stay in component APIs such
as task catalog, task context, task actions, settings, agent runtime,
harness_adapter, and workspace service. GTK code may import another component's
API, but must not import another component's `src` package.

The AI Debug tab renders runtime hook/debug events from `harness_adapter` as a
table. The task list AI column prefers the latest harness status icon when one
exists; otherwise it falls back to local terminal process state. Manual Escape
interrupts are recorded through `harness_adapter.record_harness_status()` with
the `○` icon and clear the local busy state.

Settings includes a Profiling page for GTK runtime diagnostics. It records
event counters for draw, size, pointer, hover, and terminal proxy events, along
with approximate drawn area. The page can clear counters and trigger the
process-runtime stack dump crash action when a hung or hot UI needs a current
Python stack.

Codex and Claude Code VTE terminals are wrapped in the same mouse proxy. The
proxy shields passive pointer traffic while the terminal is idle and lets the
terminal become interactive through the existing click/focus path. This keeps
the optimization scoped to embedded agent terminals; ordinary shell terminals
are not wrapped.

The Artifacts tab supports text filtering by artifact name/path and extension
filtering through the extension selector. Matching groups are expanded after a
filter changes, and tree refresh tries to preserve focus and scroll position
when the focused item still exists.

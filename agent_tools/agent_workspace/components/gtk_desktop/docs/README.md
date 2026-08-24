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

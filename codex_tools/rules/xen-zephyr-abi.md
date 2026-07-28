# Xen/Zephyr ABI Workflow

These rules apply before working with any Xen and Zephyr runtime combination in
this workspace, including QEMU smoke tests, Zephyr Dom0 management code,
zephyr-xenlib usage, DomU creation, console collection, and hypercall
validation.

1. Verify the Xen control ABI before debugging behavior. Compare the Zephyr
   Dom0 build values `CONFIG_XEN_DOMCTL_INTERFACE_VERSION` and
   `CONFIG_XEN_SYSCTL_INTERFACE_VERSION` from `.config` or `autoconf.h` with
   `XEN_DOMCTL_INTERFACE_VERSION` and `XEN_SYSCTL_INTERFACE_VERSION` from the
   exact Xen public headers used by the Xen image being booted.
2. Do this check before investigating XSM or FLASK policy, domids, magic pages,
   grant tables, console rings, image loading, FDT generation, or watchdog and
   other hypercall behavior.
3. Treat a mismatch as a hard blocker for runtime conclusions. Xen can reject
   `domctl` or `sysctl` calls before domain creation and policy logic run, so
   errors such as `-EACCES` may be ABI drift rather than a policy or feature
   bug.
4. Record the checked ABI values and the Xen version or header source in the
   task `TASK_CONTEXT.md` when runtime debugging depends on Dom0 control calls.

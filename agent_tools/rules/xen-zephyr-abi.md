---
sync: skill
---

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
4. Record the checked ABI values and the Xen version or header source through
   the task context journal when runtime debugging depends on Dom0 control
   calls.
5. Before editing or validating a Zephyr/Xen runtime harness, verify which
   Zephyr module repositories the build actually uses. Do not infer this from
   the task's review repository name. Inspect the build directory's
   `CMakeCache.txt` and `compile_commands.json` first:

   ```sh
   rg -n 'EXTRA_ZEPHYR_MODULES|ZEPHYR_EXTRA_MODULES' path/to/build/CMakeCache.txt
   rg -n 'xenstore_srv.c|xenstore_cli.c|zephyr-xenlib' path/to/build/compile_commands.json
   ```

   The source path in `compile_commands.json` is authoritative for that build.
   If Dom0 and DomU builds use different module checkouts, apply runtime fixes
   to the checkout used by the relevant build, or reconfigure the build with an
   explicit `EXTRA_ZEPHYR_MODULES` value before drawing runtime conclusions.
6. When a task has both a review checkout and a harness/build checkout, record
   the mapping through the task context journal: which repository is reviewed,
   which repository builds Dom0, which repository builds DomU, and which
   `compile_commands.json` belongs to each side. Treat a mismatch between the
   edited file and the compiled file as a hard validation blocker.
7. For Xen/Zephyr runtime tasks, build target artifacts through a task-owned
   Moulin product under the task's `dev/` directory by default. This applies
   even when the runtime starts small: the product is the reproducible record
   of the Xen image, QEMU selection, Zephyr Dom0/DomU images, generated device
   trees, initramfs images, launch scripts, and runtime helpers used by the
   task. Use direct ad hoc build directories only for explicitly scoped
   one-off experiments, and record that exception through the task context
   journal.
8. Build and run that Moulin product inside a reusable Docker-backed
   environment from the `environments` PAF domain. If no suitable environment
   exists, extend the closest matching environment or create a new one before
   treating runtime results as reproducible.
9. The runtime harness must expose a stable task-facing PAF scenario that
   launches QEMU with Xen and the selected target domains from inside the
   Docker environment. The scenario must declare the target artifacts and domain
   roles it consumes instead of relying on manual host paths or stale local
   outputs.
10. Do not assemble validations from stale artifacts, manual loader paths, or
    ad hoc build directories outside the product. The product must declare
    every source checkout, Yocto layer, Zephyr build, Linux/initramfs build,
    generated DTB, launch script, and runtime helper it depends on, so a later
    validation can be reproduced by rebuilding the product.
11. When a runtime investigation needs additional domains such as a Linux
   control/service domain, XenStore domain, driver domain, PV disk backend, or
   console collection domain, model those domains as explicit product
   components instead of modifying an unrelated Zephyr Dom0 harness. Record
   through the task context journal which domain owns each role:
   control/toolstack, hardware, XenStore server, console collector, backend
   provider, and tested client.

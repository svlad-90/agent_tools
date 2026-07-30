# Xen Findings

These findings apply to Xen, Zephyr Dom0/DomU, QEMU runtime products,
XenStore, hypercalls, console collection, and related validation harnesses.

## Xen/Zephyr control ABI versions

When changing Xen versions, compare Zephyr's Xen control ABI config with the
matching Xen public headers before debugging higher-level runtime behavior.

Check at least:

- Zephyr `CONFIG_XEN_DOMCTL_INTERFACE_VERSION` matches Xen
  `XEN_DOMCTL_INTERFACE_VERSION`.
- Zephyr `CONFIG_XEN_SYSCTL_INTERFACE_VERSION` matches Xen
  `XEN_SYSCTL_INTERFACE_VERSION`.
- The Zephyr public `domctl.h` / `sysctl.h` struct layout is compatible with
  the Xen version being tested.

Known failure shape:

- XenStore client appears to connect, but first request hangs.
- Dom0 never actually starts the XenStore server because early domctl/sysctl
  calls fail.
- Xen may return `-EACCES` for mismatched control ABI versions.

## Xen 4.21 ARM dynamic DomU console needs trap-unmapped flag

When a Zephyr Dom0 creates an ARM HVM DomU dynamically on Xen 4.21, do not
assume that `XEN_DOMCTL_CDF_hvm | XEN_DOMCTL_CDF_hap` is enough for the shared
Xen console page. The dynamic domain should also be created with
`XEN_DOMCTL_CDF_trap_unmapped_accesses`, matching the important behavior Xen
uses for dom0less ARM guests.

Known validated setup:

- Xen runtime: Xen 4.21.1 on QEMU `generic-armv8-xt`.
- Zephyr branch: `backport_headers_main` at
  `568627259dbe0fa84bd1e6c4cdce398a1817cb1a`.
- `zephyr-xenlib` module: main head
  `583e266c12166b6220b53199f8c36c1b5adb5c73`.
- Dom0 role: Zephyr Dom0 with domain management, XenStore server, console
  server, and harness autostart.
- DomU role: Zephyr `xenvm/xenvm/gicv3` log probe using Xen early console /
  `printk`.
- Required DomU creation flags:
  `XEN_DOMCTL_CDF_hvm | XEN_DOMCTL_CDF_hap |
  XEN_DOMCTL_CDF_trap_unmapped_accesses`.

Failure shape when the trap-unmapped flag is missing:

- Dom0 can create DomU and attach the DomU console.
- HVM console parameters can still look correct:
  `HVM_PARAM_CONSOLE_PFN=0x39000` and `HVM_PARAM_CONSOLE_EVTCHN=2`.
- DomU may execute normally; a normal RAM sentinel can prove `main()` ran.
- The collected `domu1` stream is still zero bytes.
- A direct DomU probe of the console page can read all ones, for example
  `out_prod=0xffffffff` and `out[0]=0xff`, while Dom0-visible console ring
  counters do not advance.

Why this is misleading:

- Xen 4.21's ARM unmapped-access fallback returns all ones on reads and ignores
  writes when the domain is not configured to trap unmapped accesses. That can
  make the DomU console page look mapped enough to read, while all writes to
  the shared console ring are effectively dropped.
- The HVM console PFN/event-channel ABI is not the suspected change here; in
  the validated case, the console PFN/event-channel values were present and the
  missing domain creation flag was the runtime blocker.

Practical checklist:

- Before debugging Zephyr logging, event channels, magic page allocation, or
  cache maintenance, print the DomU creation flags and confirm the trap flag is
  present.
- If Dom0 says `attached DomU1 console` but the harness reports zero `domu1`
  bytes, check for `XEN_DOMCTL_CDF_trap_unmapped_accesses` first.
- Keep cache flush byte-count fixes separate in reasoning. Passing
  `nr_pages * XEN_PAGE_SIZE` to `arch_dcache_flush_and_invd_range()` is a valid
  Zephyr API fix, but it was not the root cause of this Xen 4.21 zero-log
  failure.
- Evidence from the original task:
  `backport-headers-main/report/runtime/xen421-clean-trap-delay-domu-console-pass.log`
  passed with `DOMU_LOG_PROBE START`, `DOMU_LOG_PROBE FEED`,
  `DOMU_LOG_PROBE DONE: PASS`, and `source domu1 (22 lines, 1707 bytes)`.

## Zephyr DomU board GIC must match the Xen/QEMU GIC

When a Zephyr DomU is booted under an ARM Xen/QEMU product, verify that the
Zephyr board variant uses the same Generic Interrupt Controller version as the
QEMU machine that Xen is running on. The Generic Interrupt Controller, or GIC,
is the interrupt distributor that delivers timer, event-channel, and device
interrupts to the guest CPU. If Zephyr is built for the wrong GIC version, the
guest can print early boot messages and still fail once it needs normal kernel
interrupts.

Validated failure shape:

- Xen/QEMU product used `-machine virt,gic-version=3`.
- Zephyr DomU was built for the base `xenvm` board, which selected GICv2:
  `CONFIG_GIC_V2=y`, `CONFIG_GIC_VER=2`.
- Zephyr printed early Xen and UART messages, `xs_init()` could return `0`,
  and HVM store parameters were visible.
- `k_sleep(K_MSEC(1000))` never returned, Zephyr log timestamps stayed at
  `00:00:00.000`, and XenStore request timeouts did not fire. This can look
  like a XenStore client hang, but the scheduler timeout path is blocked before
  XenStore behavior can be judged.

Practical checklist:

- Before debugging XenStore request/response logic, add or inspect a simple
  Zephyr timer checkpoint such as `k_sleep(K_MSEC(1000))` followed by a
  `printk()` marker.
- Compare QEMU/Xen GIC selection with the Zephyr build output:
  - QEMU launch should show the machine GIC version, for example
    `gic-version=3`.
  - Zephyr `.config` should match, for example `CONFIG_GIC_V3=y` and
    `CONFIG_GIC_VER=3` for a GICv3 product.
  - Zephyr `zephyr.dts` should show `compatible = "arm,gic-v3", "arm,gic"`
    for the interrupt controller when the product uses GICv3.
- For the Zephyr `xenvm` board in the validated product, use the GICv3
  qualified board target `xenvm/xenvm/gicv3`, not plain `xenvm`.
- Treat a stuck `k_sleep()` or non-moving Zephyr log timestamp as an interrupt
  controller or timer setup problem first. Do not tune XenStore client
  timeouts or response polling until the timer checkpoint passes.

Evidence from the original task:

- Product path:
  `zephyr-xenstore-client/dev/qemu-xen-linux-service-zephyr-domu-validation`.
- Broken diagnostic log:
  `report/runtime/qemu-xen421-zephyr-vpl011-timer-check-60s.log` stopped at
  `pr103_case: timer-sleep START`.
- Fixed diagnostic log:
  `report/runtime/qemu-xen421-zephyr-vpl011-gicv3-60s.log` showed Zephyr built
  with board qualifiers `xenvm/gicv3`, built `intc_gicv3.c.obj`, and printed
  `pr103_case: timer-sleep PASS`.
- Source fix used by that task:
  `ZEPHYR_DOMU_BOARD: "xenvm/xenvm/gicv3"` in the Moulin product YAML.

## Xen serial-switch logs are evidence, not exact domain ownership

When QEMU stdio is multiplexed between Xen and guest serial consoles, the Xen
`Serial input to DOM<N>` message changes which guest receives keyboard input.
It does not guarantee that every following line without an explicit `DOM<N>:`
prefix was produced by that guest. The workspace harness keeps one combined
log and tags lines by a best-effort active-source model, so source labels are
useful for navigation but should not be the only evidence for domain ownership.

Known misleading shape:

- Xen prints explicit lines such as `(XEN) DOM1: ...` or `(XEN) DOM2: ...`.
  Those prefixes are stronger evidence than the harness-added `[domu1]` or
  `[domu2]` classification.
- After a scheduled Ctrl-A serial switch, host-side status lines such as
  `QEMU_SMOKE_RC=124` can be tagged under the last active guest even though
  they were emitted by the shell wrapper.
- Interleaved Linux and Zephyr VPL011 output can appear under the current
  active input domain if the raw line does not carry an explicit Xen `DOM<N>:`
  prefix.

Practical checklist:

- For runtime conclusions, grep the raw log for semantic markers, not only for
  harness source labels. Examples: `DOM2: PR103 REVIEW PROBE START`,
  `DOM2: pr103_case: timer-sleep PASS`,
  `DOM1: Finished Introduce dom0less guests to xenstored`, and host
  `QEMU_SMOKE_RC=124`.
- Treat explicit Xen prefixes such as `(XEN) DOM2:` as stronger evidence than
  the harness source bucket shown at the left edge.
- When a test depends on seeing a guest, require both a guest-specific marker
  and a transport marker such as `Serial input to DOM2`. Do not infer that a
  missing marker means the guest did not run until the console path is proven.
- Keep Ctrl-A switching in task-local harness scripts or scenarios. Do not add
  direct hypervisor-console calls to production Zephyr samples just to make a
  batch log easier to read.

## Zephyr XenStore server `XS_RM` missing-node errors

When testing remove/delete behavior, verify the server commit being tested
before choosing the expected missing-node errno.

Historical failure shape:

- Older Zephyr XenStore server code called `key_to_entry_check_perm()` from
  `xss_do_rm()`.
- That helper returned one `NULL` result both when the node was missing and
  when write permission was missing.
- `xss_do_rm()` converted that `NULL` to `-EINVAL`, so a missing remove target
  did not produce a clear missing-node error.

Practical checklist:

- In the current task series, commit `xenstore-srv: fix remove request
  handling` splits lookup from permission checking.
- For that current series, expect `xs_client_rm(missing_child)` to return
  `-ENOENT`.
- If an old build returns `-EINVAL`, check whether it contains the split
  lookup/permission fix in `xss_do_rm()`.

## Zephyr XenStore server transaction messages

Do not expose or test client transaction helpers as real transactions until the
server implements real transaction semantics.

Current server behavior to remember:

- The server has transaction message handling surface.
- It does not provide real staging, commit, abort, or rollback behavior for
  store mutations.

Practical checklist:

- Keep public client transaction helpers out of the API while validating
  against this server.
- Treat transaction support as a separate server feature, not as a client-side
  wrapper around ordinary requests.

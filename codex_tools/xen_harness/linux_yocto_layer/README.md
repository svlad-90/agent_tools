# Xen Harness Linux Yocto Layer

This directory contains a reusable Yocto layer for Linux Dom0 validation
products that need per-DomU console collection.

Add `meta-xen-harness` to the product `bblayers.conf`, then add the package to
the Dom0 image:

```bitbake
IMAGE_INSTALL:append = " xen-harness-console"
```

The installed `xen-harness-console.service` starts after `xenconsoled` and
runs `/usr/libexec/xen-harness/collect-consoles.sh`. The default configuration
collects DomU 1:

```sh
XEN_HARNESS_CONSOLE_DOMIDS="1"
XEN_HARNESS_CONSOLE_OUTPUT="console"
XEN_HARNESS_CONSOLE_BACKEND="auto"
XEN_HARNESS_CONSOLE_ONESHOT="0"
```

`console` output uses the same framing as the Zephyr Dom0 harness module:

```text
[xen-harness][domu1] guest log line
```

`XEN_HARNESS_CONSOLE_BACKEND=auto` starts both supported Linux collectors.
The `xenconsole` collector follows standard Xen PTYs created by `xenconsoled`
for toolstack-managed guests. The `xen-dmesg` collector follows Xen's
hypervisor log through `xl dmesg` and re-emits `(XEN) DOM<N>:` guest records;
this is the useful path for dom0less ARM guests that expose VPL011 output but
do not have `/local/domain/<domid>/console/tty` in XenStore.

Set `XEN_HARNESS_CONSOLE_BACKEND=xen-dmesg` and
`XEN_HARNESS_CONSOLE_ONESHOT=1` for deterministic smoke checks that should dump
the current Xen ring once and return to the shell.

The Python harness already recognizes those records as source `domu1`. Products
with a host-visible file transport may set `XEN_HARNESS_CONSOLE_OUTPUT=file`
and tail `/run/xen-harness/console/domu<N>.log` through their own export path.

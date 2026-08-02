# Environments PAF Domain

This domain owns reusable execution substrates: Docker images, container
aliases, toolchain smoke checks, and build commands that are shared by product
domains. Product domains should reference container aliases from this domain
instead of calling shell scripts under `codex_tools/environments`.

The domain exposes:

```text
tasks.py      PAF task classes
lib/          Python command builders used by tasks
assets/       Dockerfiles and environment source assets
scenarios/    runnable environment checks
profiles/     reusable environment YAML profiles
```

`zephyr-xen` provides a Zephyr SDK, west, CMake, Ninja, QEMU, and Python clang
bindings. The default container alias is `zephyr-xen-workspace`, with the host
workspace mounted at `/home/builder/workspace`.

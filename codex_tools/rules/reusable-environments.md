# Reusable environment workflow

These rules apply when a task depends on a non-trivial local environment such
as a cross toolchain, SDK, emulator, hypervisor, CI runner, or generated build
context.

1. If the same environment issue blocks more than one task, stop treating it
   as a task-local inconvenience. Fix the environment problem directly before
   continuing with more task work.
2. Fix recurring environment problems in a reusable form that is fully
   portable without an AI agent. A human should be able to clone or copy the
   workspace, run the documented script, and either verify that the environment
   exists or build it from the checked-in files.
3. The Dockerfile is the source of truth for Docker-based environments. Do not
   depend on an image that only exists in one local Docker daemon unless the
   checked-in environment can rebuild an equivalent image from its Dockerfile.
   Pin versions and install every required tool explicitly enough that the
   image can be recreated later.
4. Store reusable workspace environment automation under
   `codex_tools/paf_workspace/domains/environments/`. Each environment should
   have Dockerfile/source assets under `assets/<environment>/`, PAF task entry
   points in `tasks.py`, and reusable Python implementation under `lib/`.
   Historical `codex_tools/environments/` directories are legacy locations and
   should not be used for new orchestration.

   ```text
   domains/environments/
     tasks.py
     lib/
     assets/<environment>/Dockerfile
     assets/<environment>/README.md
     scenarios/*.xml
     profiles/*.yaml
   ```

5. Every reusable environment must provide PAF task entry points with stable
   behavior where they apply: image check without build, image ensure/build,
   tool smoke check, shell/command execution when needed, and normal validation
   such as generating a Zephyr compile database. Shared command construction
   belongs in Python under `lib/`, not in shell scripts.
6. Docker-based environments must be built with working DNS inside Docker
   build containers. The PAF build/ensure task should perform or delegate a
   small DNS preflight from Docker before starting a long build, and the actual
   `docker build` invocation must use an explicit network selection. Default
   the network to a mode with known working DNS for the environment, commonly
   `host` on local Linux workstations, and document how to override it.

   If package mirrors, source archives, or language package indexes fail
   because DNS resolution does not work, stop and fix Docker DNS for the
   environment instead of working around the failure with ad hoc host downloads
   or partially built images.
7. Keep task-specific build outputs, logs, temporary worktrees, and runtime
   artifacts inside the task directory. The reusable environment domain should
   contain only the machinery needed to recreate the environment.
8. When an environment is meant to support C or C++ work, include enough setup
   to generate a usable `compile_commands.json` for `cpp_code_map`. For Zephyr
   work this includes the Zephyr SDK, `west`, generated headers, and any QEMU,
   Xen, or board-specific tooling needed by the validation workflow.
9. For tasks that need a reusable build or runtime environment, first look for
   an existing matching environment profile/scenario under
   `codex_tools/paf_workspace/domains/environments/`. If none fits, extend the
   closest existing environment when the dependency set and workflow are the
   same, or create a new environment entry when the task needs a distinct
   toolchain, SDK, emulator, hypervisor, CI runner, or runtime product. Do not
   leave required target-build tooling only in task-local shell history.
10. Docker-backed environments that build target artifacts must provide a
    stable way to run workspace tools inside the image, including
    `cpp_code_map` against the generated compile database when C/C++ source
    analysis is needed.
11. Document the exact commands for checking, building, entering, and validating
   the environment. The README should also describe expected mount points and
   repository layout, for example which task directory is mounted as work
   input, where Zephyr repositories live, where generated build directories are
   written, and where logs are stored.
12. Agent-only notes are allowed in the README, but only as secondary guidance:
   they may explain recommended mount folders, repository placement, or common
   task layouts. They are not a substitute for runnable scripts.

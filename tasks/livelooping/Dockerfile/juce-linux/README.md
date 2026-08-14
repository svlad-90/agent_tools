# LoopRigger JUCE Linux Environment

This task-local image provides the Linux CMake/JUCE build dependencies for
LoopRigger.

Build the image from the workspace root:

```sh
tasks/livelooping/scripts/build-juce-image.sh
```

Run the default Linux build and tests:

```sh
tasks/livelooping/scripts/build-linux.sh
```

Run the JUCE app target:

```sh
tasks/livelooping/scripts/build-linux.sh juce-app
```

Run the JUCE plugin-host tests:

```sh
tasks/livelooping/scripts/build-linux.sh plugin-host
```

The scripts mount the workspace at `/work` and run inside
`/work/tasks/livelooping/dev/LoopRigger`.

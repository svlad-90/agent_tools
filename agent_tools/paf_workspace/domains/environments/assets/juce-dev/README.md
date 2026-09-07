# JUCE Development Environment

Reusable Ubuntu 24.04 Docker image for CMake/Ninja/JUCE development.

The image includes:

- workspace Python tooling and tree-sitter bindings;
- clang, libclang, and Python clang bindings for `cpp_code_map`;
- CMake, Ninja, GCC, and build-essential;
- JUCE Linux GUI/audio dependencies for ALSA, JACK, X11, GL/EGL, GTK,
  WebKit, FreeType, fontconfig, curl, and LADSPA;
- `xvfb-run` for headless GUI-oriented test runs.

Build or validate the environment from the workspace root:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/environments/scenarios/juce-dev.xml \
  validate \
  --yaml-config agent_tools/paf_workspace/domains/environments/profiles/juce-dev.yaml
```

The default container alias mounts the host workspace at the same absolute
path and starts in `${WORKSPACE_ROOT}`. Override Docker build networking with
`--parameter ENVIRONMENT_BUILD_NETWORK=<mode>` when host networking is not
available.

# JUCE Repository Validation

PAF domain for validating CMake/JUCE repositories inside the reusable
`juce-dev` Docker environment.

The default `looprigger` profile runs:

- `git diff --check`;
- CMake configure with `CMAKE_EXPORT_COMPILE_COMMANDS=ON`;
- Ninja build;
- CTest with output on failure;
- optional task context hygiene check;
- optional push-guard marker phase.

Example:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/juce_repo_validation/scenarios/looprigger.xml \
  validate \
  --yaml-config agent_tools/paf_workspace/domains/juce_repo_validation/profiles/looprigger.yaml
```

Use PAF parameter overrides to reuse the same domain for another JUCE/CMake
repository, for example:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/juce_repo_validation/scenarios/looprigger.xml \
  validate \
  --yaml-config agent_tools/paf_workspace/domains/juce_repo_validation/profiles/looprigger.yaml \
  --parameter JUCE_VALIDATE_REPO=tasks/example/dev/MyJuceRepo \
  --parameter JUCE_VALIDATE_BUILD_DIR=build-linux-juce
```

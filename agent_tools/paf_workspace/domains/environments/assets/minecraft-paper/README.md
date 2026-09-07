# Minecraft Paper Environment

Docker image for validating and smoke-testing Minecraft Paper/Purpur plugin
repositories in a reproducible Linux environment.

The image includes:

- OpenJDK 21 JDK;
- Gradle 9.7.1;
- Python 3 workspace-tool baseline;
- SQLite CLI;
- basic network/process utilities used by future headless server checks.

Build or ensure the image through PAF:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/environments/scenarios/minecraft-paper.xml \
  validate \
  agent_tools/paf_workspace/domains/environments/profiles/minecraft-paper.yaml
```

The image is intentionally generic. Repository-specific checks live in
`domains/minecraft_repo_validation`.

# Minecraft Repository Validation

PAF domain for validating Minecraft server repositories.

The first scenario targets `mc.slayerworld` and runs repository checks inside
the reusable `minecraft-paper` Docker environment:

- Git whitespace check;
- Python config validation;
- server assembly dry run with missing private artifacts allowed;
- Gradle `test jar` for `plugins/frontline-factions`;
- self-contained SQLite bundle check for the produced plugin jar;
- Paper runtime smoke that boots a real server with the produced plugin;
- optional task context hygiene check;
- optional push-guard marker phase.

Example:

```sh
agent_tools/paf_workspace/run-paf.sh \
  agent_tools/paf_workspace/domains/minecraft_repo_validation/scenarios/mc-slayerworld.xml \
  validate \
  agent_tools/paf_workspace/domains/minecraft_repo_validation/profiles/mc-slayerworld.yaml
```

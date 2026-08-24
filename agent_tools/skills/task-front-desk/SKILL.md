---
name: task-front-desk
description: Legacy fallback for manually driving old task-local front_door_bell.py scripts when harness hooks are unavailable and the user explicitly asks for the fallback protocol.
rule: agent_tools/rules/task-workflow.md
---

# Task Front Desk

Normal workspace tasks do not use this skill. Agent Workspace policy is now
hook-driven through `agent_tools.agent_workspace.components.harness_adapter`.
Use this skill only for old local tasks when harness hooks are unavailable and
the user explicitly asks to drive the legacy manual fallback.

For that fallback, the task-local entrypoint is `front_door_bell.py` in the
task directory. Run it with the available Python interpreter:

```sh
python3 front_door_bell.py --open-iteration
```

If the host uses a different Python launcher, use that launcher with the same
task-local script.

## Protocol

1. Run `front_door_bell.py --open-iteration` only when using the legacy
   fallback.
2. Follow the returned `FRONT_DESK_STAGE`.
3. Treat one iteration as one useful work step for the latest user request,
   followed by returning control to the user.
4. Do not consider the iteration complete until the tool returns
   `ITERATION_DONE` or `BLOCKED`.
5. If the tool returns task_check failures, fix those failures before normal
   task work.
6. If the tool returns `DO_USER_WORK`, execute the user's request. Re-read
   current context slots only when prior decisions, findings, validation,
   environment, risks, or current task state matter.
7. If the tool returns `JOURNAL_REQUIRED`, update singleton task context slots
   in place. Minimum slot for substantive work is `operational-memory`; update
   `findings`, `decisions`, `validation`, or `blocker-risk` when those facts
   changed.
8. If the user request required no durable context update, run:

   ```sh
   python3 front_door_bell.py --ack-no-context-change
   ```

9. If an older pending iteration must be abandoned, run:

   ```sh
   python3 front_door_bell.py --close-iteration
   ```

10. After the tool returns `ITERATION_DONE`, answer the user concisely.

The tool output is for the agent, not for the human user. Do not paste the full
tool protocol back to the user unless asked.

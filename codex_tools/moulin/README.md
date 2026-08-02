# Moulin local validation notes

The reusable environment lives in the PAF `environments` domain as
`moulin-act`. Use the compatibility wrapper `run-act-build.sh` instead of
manually typing the full `act` command. The wrapper calls the PAF scenario,
which builds or reuses the local `moulin-act:22.04` image and runs the real
GitHub Actions `build` job.

Example:

```sh
./codex_tools/moulin/run-act-build.sh ./path/to/moulin-worktree
```

Use the PAF `validate` scenario after changing the environment Dockerfile; it
ensures the image before running `act`.

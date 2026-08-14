# Task Description

## Request

- Work with the LoopRigger repository:
  `git@github.com:svlad-90/LoopRigger.git`.
- Build and validate on Linux.
- A newer project copy may exist on a Windows machine reachable by SSH at:
  `C:\Users\svlad\dev\LoopRigger`.
- Windows SSH access:
  `ssh -i ~/.ssh/id_rsa svlad@192.168.150.1`.
- Compare or import needed changes from the Windows copy when SSH access is
  available.

## Scope

- In scope:
  - Create or update the Linux workspace checkout under this task.
  - Identify build requirements and run the Linux build path.
  - Compare the Linux checkout with the newer Windows copy if access details
    are provided.
- Out of scope:
  - Pushing changes unless explicitly requested.

## Acceptance Criteria

- Repository checkout is available under `dev/`.
- Linux build command is identified and run, or the blocker is recorded.
- Any required changes from the Windows copy are identified or imported.

## Background

- Windows project path: `C:\Users\svlad\dev\LoopRigger`.

## References

- Upstream repository: `git@github.com:svlad-90/LoopRigger.git`.

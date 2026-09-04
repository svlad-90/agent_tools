from __future__ import annotations

import json
from pathlib import Path

from agent_tools.tools import push_guard

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import bool_arg, optional_string_arg, resolve_workspace_path, string_arg


def push_guard_tools() -> list[McpTool]:
    return [
        McpTool(
            name="push_guard_status",
            title="Push Guard Status",
            description=(
                "Use before pushing to check whether a commit already has a "
                "workspace validation stamp. Avoids manually inspecting .git "
                "metadata and returns compact recorded/not-recorded status."
            ),
            input_schema=_repo_ref_input_schema(),
            handler=_push_guard_status,
        ),
        McpTool(
            name="push_guard_mark_success",
            title="Push Guard Mark Success",
            description=(
                "Use after an explicit successful validation run to stamp a commit "
                "for push_guard. Prefer validate_changed/validate_task with "
                "mark_push_guard when running checks now."
            ),
            input_schema=_mark_success_input_schema(),
            handler=_push_guard_mark_success,
        ),
        McpTool(
            name="push_guard_check_staged",
            title="Push Guard Check Staged",
            description=(
                "Use instead of manual pre-commit scans. Checks staged files and "
                "task_check blockers, returning compact actionable findings."
            ),
            input_schema=_check_staged_input_schema(),
            handler=_push_guard_check_staged,
        ),
        McpTool(
            name="push_guard_check",
            title="Push Guard Check",
            description=(
                "Use instead of manually parsing pre-push refs. Checks pushed commits "
                "for missing validation stamps, guarded files, and task_check "
                "blockers."
            ),
            input_schema=_check_input_schema(),
            handler=_push_guard_check,
        ),
        McpTool(
            name="push_guard_install_hook",
            title="Push Guard Install Hook",
            description=(
                "Use to install or refresh Agent Workspace pre-commit and pre-push "
                "hooks for one known repository root."
            ),
            input_schema=_repo_input_schema(),
            handler=_push_guard_install_hook,
        ),
    ]


def _push_guard_status(context: ToolContext, arguments: JsonObject) -> ToolResult:
    repo = _repo(context, arguments)
    ref = string_arg(arguments, "ref", "HEAD")
    commit = push_guard._head_commit(repo, ref)
    stamp = push_guard._stamp_path(repo, commit)
    payload: JsonObject = {
        "repo": str(repo),
        "ref": ref,
        "commit": commit,
        "stamp": str(stamp),
        "recorded": stamp.is_file(),
    }
    if stamp.is_file():
        stamp_payload = json.loads(stamp.read_text(encoding="utf-8"))
        payload["recorded_at"] = stamp_payload.get("recorded_at", "")
        payload["source"] = stamp_payload.get("source") or stamp_payload.get("command") or ""
    return ToolResult(text=_status_text(payload), structured_content=payload, is_error=not stamp.is_file())


def _push_guard_mark_success(context: ToolContext, arguments: JsonObject) -> ToolResult:
    repo = _repo(context, arguments)
    ref = string_arg(arguments, "ref", "HEAD")
    commit = push_guard._head_commit(repo, ref)
    receipt = optional_string_arg(arguments, "receipt")
    if receipt:
        source = push_guard._validated_receipt_source(
            repo,
            commit,
            _resolve_repo_path(repo, receipt),
        )
    else:
        source = string_arg(arguments, "source", "external validation")
    push_guard._record_success(repo, commit, source)
    stamp = push_guard._stamp_path(repo, commit)
    payload = {
        "repo": str(repo),
        "ref": ref,
        "commit": commit,
        "source": source,
        "stamp": str(stamp),
    }
    return ToolResult(
        text=f"push_guard: recorded successful validation for {commit}\npush_guard: source: {source}\n",
        structured_content=payload,
    )


def _push_guard_check_staged(context: ToolContext, arguments: JsonObject) -> ToolResult:
    repo = _repo(context, arguments)
    findings = push_guard._guarded_staged_file_findings(repo)
    task_check_report = push_guard._task_check_report_for_repo(repo)
    allow_override = bool_arg(arguments, "allow_override", False)
    blocked = bool(findings or task_check_report)
    is_error = blocked and not allow_override
    payload = {
        "repo": str(repo),
        "allow_override": allow_override,
        "findings": [_finding_json(finding) for finding in findings],
        "task_check_report": task_check_report or "",
        "blocked": blocked,
    }
    return ToolResult(text=_check_text("commit", payload), structured_content=payload, is_error=is_error)


def _push_guard_check(context: ToolContext, arguments: JsonObject) -> ToolResult:
    repo = _repo(context, arguments)
    stdin_text = string_arg(arguments, "stdin", "")
    allow_override = bool_arg(arguments, "allow_override", False)
    commits = push_guard._pushed_commits(stdin_text, repo)
    ref_tips = push_guard._pushed_ref_tips(stdin_text, repo)
    findings = push_guard._guarded_pushed_file_findings(repo, commits)
    task_check_report = push_guard._task_check_report_for_repo(repo)
    missing = [commit for commit in ref_tips if not push_guard._stamp_path(repo, commit).is_file()]
    blocked = bool(findings or task_check_report or missing)
    is_error = blocked and not allow_override
    payload = {
        "repo": str(repo),
        "allow_override": allow_override,
        "commits": commits,
        "ref_tips": ref_tips,
        "missing_validation": missing,
        "findings": [_finding_json(finding) for finding in findings],
        "task_check_report": task_check_report or "",
        "blocked": blocked,
    }
    return ToolResult(text=_check_text("push", payload), structured_content=payload, is_error=is_error)


def _push_guard_install_hook(context: ToolContext, arguments: JsonObject) -> ToolResult:
    repo = _repo(context, arguments)
    push_guard.install_repo_hooks(repo)
    hooks_dir = push_guard.git_path(repo, "hooks")
    payload = {
        "repo": str(repo),
        "hooks": [str(hooks_dir / "pre-commit"), str(hooks_dir / "pre-push")],
    }
    return ToolResult(
        text="\n".join(f"push_guard: installed {path}" for path in payload["hooks"]) + "\n",
        structured_content=payload,
    )


def _repo(context: ToolContext, arguments: JsonObject) -> Path:
    repo = resolve_workspace_path(context.workspace, string_arg(arguments, "repo", "."))
    return push_guard._repo_root(repo)


def _resolve_repo_path(repo: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo / path
    resolved = path.resolve()
    try:
        resolved.relative_to(repo)
    except ValueError as error:
        raise ValueError(f"path is outside repo: {value}") from error
    return resolved


def _finding_json(finding: push_guard.PushedFileFinding) -> JsonObject:
    return {"path": finding.path, "reason": finding.reason}


def _status_text(payload: JsonObject) -> str:
    lines = [
        f"push_guard: repo: {payload['repo']}",
        f"push_guard: commit: {payload['commit']}",
        f"push_guard: stamp: {payload['stamp']}",
        f"push_guard: status: {'recorded' if payload['recorded'] else 'missing'}",
    ]
    if payload["recorded"]:
        lines.append(f"push_guard: recorded_at: {payload.get('recorded_at', '<unknown>')}")
        lines.append(f"push_guard: source: {payload.get('source', '<unknown>')}")
    return "\n".join(lines) + "\n"


def _check_text(action: str, payload: JsonObject) -> str:
    lines = [f"push_guard: {action} {'blocked' if payload['blocked'] else 'allowed'}"]
    for finding in payload["findings"]:
        lines.append(f"  {finding['path']}: {finding['reason']}")
    if payload.get("missing_validation"):
        lines.append("missing successful validation:")
        lines.extend(f"  {commit}" for commit in payload["missing_validation"])
    if payload.get("task_check_report"):
        lines.append("task_check report:")
        lines.append(str(payload["task_check_report"]).rstrip())
    if payload["allow_override"] and payload["blocked"]:
        lines.append("push_guard: override enabled")
    return "\n".join(lines) + "\n"


def _repo_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "default": ".",
                "description": "Workspace-relative or absolute path inside the git repository.",
            },
        },
        "additionalProperties": False,
    }


def _repo_ref_input_schema() -> JsonObject:
    schema = _repo_input_schema()
    schema["properties"]["ref"] = {
        "type": "string",
        "description": "Git ref or commit to inspect or stamp.",
        "default": "HEAD",
    }
    return schema


def _mark_success_input_schema() -> JsonObject:
    schema = _repo_ref_input_schema()
    schema["properties"].update(
        {
            "source": {
                "type": "string",
                "default": "external validation",
                "description": "Human-readable validation source recorded in the stamp when no receipt is provided.",
            },
            "receipt": {
                "type": "string",
                "description": "Repo-relative or absolute validation receipt JSON used as stamp evidence.",
            },
        }
    )
    return schema


def _check_staged_input_schema() -> JsonObject:
    schema = _repo_input_schema()
    schema["properties"]["allow_override"] = {
        "type": "boolean",
        "description": "Return success even when blockers exist; only use for explicit manual override flows.",
        "default": False,
    }
    return schema


def _check_input_schema() -> JsonObject:
    schema = _check_staged_input_schema()
    schema["properties"]["stdin"] = {
        "type": "string",
        "default": "",
        "description": "Pre-push hook stdin text. Empty input checks HEAD.",
    }
    return schema

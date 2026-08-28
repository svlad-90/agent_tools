from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from ...settings.api import load_agent_workspace_settings
from ...settings.api import remember_agent_workspace


AGENT_WORKSPACE_MANIFEST_DIR = ".agent-workspace"
AGENT_WORKSPACE_MANIFEST_FILE = "workspace.json"
AGENT_WORKSPACE_SCHEMA_VERSION = 1
AGENT_WORKSPACE_MIN_VERSION = "2.1.0"
DEFAULT_TASKS_DIR = "tasks"


@dataclass(frozen=True)
class AgentWorkspaceManifest:
    schema_version: int
    workspace_id: str
    name: str
    created_at: str
    agent_workspace_min_version: str
    tasks_dir: str = DEFAULT_TASKS_DIR


def agent_workspace_manifest_path(workspace: Path) -> Path:
    return workspace / AGENT_WORKSPACE_MANIFEST_DIR / AGENT_WORKSPACE_MANIFEST_FILE


def is_agent_workspace(workspace: Path) -> bool:
    path = workspace.resolve()
    return agent_workspace_manifest_path(path).is_file() or (path / DEFAULT_TASKS_DIR).is_dir()


def create_agent_workspace(workspace: Path, *, name: str | None = None) -> AgentWorkspaceManifest:
    root = workspace.resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / DEFAULT_TASKS_DIR).mkdir(exist_ok=True)
    manifest = AgentWorkspaceManifest(
        schema_version=AGENT_WORKSPACE_SCHEMA_VERSION,
        workspace_id=str(uuid4()),
        name=(name or root.name or "Agent Workspace").strip(),
        created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        agent_workspace_min_version=AGENT_WORKSPACE_MIN_VERSION,
        tasks_dir=DEFAULT_TASKS_DIR,
    )
    _write_manifest(root, manifest)
    return manifest


def ensure_agent_workspace(workspace: Path) -> AgentWorkspaceManifest:
    root = workspace.resolve()
    manifest_path = agent_workspace_manifest_path(root)
    if manifest_path.is_file():
        manifest = load_agent_workspace_manifest(root)
        (root / manifest.tasks_dir).mkdir(parents=True, exist_ok=True)
        return manifest
    return create_agent_workspace(root)


def load_agent_workspace_manifest(workspace: Path) -> AgentWorkspaceManifest:
    root = workspace.resolve()
    manifest_path = agent_workspace_manifest_path(root)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"workspace manifest is not an object: {manifest_path}")
    schema_version = data.get("schema_version")
    workspace_id = data.get("workspace_id")
    name = data.get("name")
    created_at = data.get("created_at")
    min_version = data.get("agent_workspace_min_version")
    tasks_dir = data.get("tasks_dir", DEFAULT_TASKS_DIR)
    if schema_version != AGENT_WORKSPACE_SCHEMA_VERSION:
        raise ValueError(f"unsupported workspace schema version in {manifest_path}: {schema_version!r}")
    if not isinstance(workspace_id, str) or not workspace_id.strip():
        raise ValueError(f"workspace manifest has no workspace_id: {manifest_path}")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"workspace manifest has no name: {manifest_path}")
    if not isinstance(created_at, str) or not created_at.strip():
        raise ValueError(f"workspace manifest has no created_at: {manifest_path}")
    if not isinstance(min_version, str) or not min_version.strip():
        raise ValueError(f"workspace manifest has no agent_workspace_min_version: {manifest_path}")
    if not isinstance(tasks_dir, str) or not tasks_dir.strip() or Path(tasks_dir).is_absolute():
        raise ValueError(f"workspace manifest has invalid tasks_dir: {manifest_path}")
    return AgentWorkspaceManifest(
        schema_version=schema_version,
        workspace_id=workspace_id.strip(),
        name=name.strip(),
        created_at=created_at.strip(),
        agent_workspace_min_version=min_version.strip(),
        tasks_dir=tasks_dir.strip(),
    )


def resolve_agent_workspace_startup(
    explicit_workspace: Path | None = None,
    *,
    cwd: Path | None = None,
) -> Path:
    candidates: list[Path] = []
    if explicit_workspace is not None:
        candidates.append(explicit_workspace)
    else:
        settings = load_agent_workspace_settings()
        last_workspace = settings.get("last_workspace")
        if isinstance(last_workspace, str) and last_workspace:
            candidates.append(Path(last_workspace))
        recent_workspaces = settings.get("recent_workspaces")
        if isinstance(recent_workspaces, list):
            for item in recent_workspaces:
                if isinstance(item, str) and item:
                    candidates.append(Path(item))
        candidates.append(cwd or Path.cwd())

    for candidate in candidates:
        root = candidate.expanduser().resolve()
        if is_agent_workspace(root) or explicit_workspace is not None:
            ensure_agent_workspace(root)
            remember_agent_workspace(root)
            return root

    root = (cwd or Path.cwd()).expanduser().resolve()
    ensure_agent_workspace(root)
    remember_agent_workspace(root)
    return root


def _write_manifest(workspace: Path, manifest: AgentWorkspaceManifest) -> None:
    manifest_path = agent_workspace_manifest_path(workspace)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": manifest.schema_version,
        "workspace_id": manifest.workspace_id,
        "name": manifest.name,
        "created_at": manifest.created_at,
        "agent_workspace_min_version": manifest.agent_workspace_min_version,
        "tasks_dir": manifest.tasks_dir,
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

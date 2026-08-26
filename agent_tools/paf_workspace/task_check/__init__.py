from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from agent_tools.tools.task_context import DATABASE_FILENAME as TASK_CONTEXT_DATABASE_FILE
from agent_tools.tools.task_context import RECOMMENDED_SLOT_CATEGORIES
from agent_tools.tools.task_context import REQUIRED_SLOT_CATEGORIES
from agent_tools.tools.task_context import SLOT_CATEGORIES
from agent_tools.tools.task_context import TaskContextSlot
from agent_tools.tools.task_context import ensure_database as ensure_task_context_database
from agent_tools.tools.task_context import load_slots as load_task_context_slots
from agent_tools.tools.task_actualize import actualize_task


REQUIRED_DIRS = ("dev", "Dockerfile", "scripts", "report", "report/diff", "report/puml")
TASK_METADATA_FILE = "TASK_METADATA.json"
RUNTIME_HINTS = ("xen", "qemu", "moulin", "dom0", "domu", "hypervisor")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PAF_WORKSPACE_ROOT = PROJECT_ROOT / "agent_tools" / "paf_workspace"
PRODUCT_ARTIFACTS_TEMPLATE = PAF_WORKSPACE_ROOT / "templates" / "product-artifacts.yaml"
DEFAULT_RUNTIME_YAML_NAME = "xen-zephyr-runtime.yaml"
TASKS_DIR_NAME = "tasks"
WARNING_POLICY_FILE = Path(__file__).with_name("warning-policy.yaml")
TASK_CONTEXT_TOTAL_CONTEXT_BUDGET = 256_000
TASK_CONTEXT_ACTIVE_BUDGET_FRACTION = 0.10
TASK_CONTEXT_ACTIVE_TOKEN_BUDGET = int(TASK_CONTEXT_TOTAL_CONTEXT_BUDGET * TASK_CONTEXT_ACTIVE_BUDGET_FRACTION)
TASK_CONTEXT_ACTIVE_SEVERITIES = ("mid", "high", "critical")


@dataclass(frozen=True)
class Check:
    status: str
    code: str
    message: str
    path: str | None = None

    def as_dict(self) -> dict[str, str]:
        result = {
            "status": self.status,
            "code": self.code,
            "message": self.message,
        }
        if self.path is not None:
            result["path"] = self.path
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check workspace task layout and workflow metadata.")
    parser.add_argument("task_dir", help="Task directory to inspect.")
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace root used for relative paths. Default: current directory.",
    )
    parser.add_argument("--json", action="store_true", help="Render machine-readable JSON.")
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Exit non-zero when warnings are present.",
    )
    parser.add_argument(
        "--errors-only",
        action="store_true",
        help="Render only failing checks and the summary in text output.",
    )
    parser.add_argument(
        "--runtime-product",
        action="store_true",
        help="Require a product artifact manifest even if the task context has no runtime hints.",
    )
    parser.add_argument(
        "--xen-runtime",
        action="store_true",
        help="Require Xen/Zephyr runtime YAML metadata even if no profile exists yet.",
    )
    parser.add_argument(
        "--init-layout",
        action="store_true",
        help=(
            "Create missing task directories and TASK_CONTEXT.sqlite3."
        ),
    )
    parser.add_argument(
        "--privacy",
        choices=("public", "private"),
        default="public",
        help="Task visibility metadata to write when initializing layout. Default: public.",
    )
    parser.add_argument(
        "--init-runtime-product",
        action="store_true",
        help="Create runtime product manifest, Xen scenario directory, starter scenario, and runtime report directory.",
    )
    parser.add_argument(
        "--env-check-command",
        action="store_true",
        help="Print the PAF environment-domain check command without running it.",
    )
    parser.add_argument(
        "--run-env-check",
        action="store_true",
        help="Run the PAF environment-domain check command. This does not build images.",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    workspace = Path(args.workspace).resolve()
    task_dir = _resolve_task_dir(workspace, args.task_dir)
    init_checks: list[Check] = []
    if args.init_layout or args.init_runtime_product:
        init_checks = initialize_task_layout(task_dir, workspace=workspace, privacy=args.privacy)
    if args.init_runtime_product:
        init_checks.extend(initialize_runtime_product(task_dir, workspace=workspace))
    checks = check_task(
        task_dir,
        workspace=workspace,
        require_runtime_product=args.runtime_product or args.init_runtime_product,
        require_xen_runtime=args.xen_runtime or args.init_runtime_product,
    )
    if args.env_check_command or args.run_env_check:
        checks.extend(check_environment_commands(task_dir, workspace=workspace, run=args.run_env_check))
    checks = [*init_checks, *checks]

    if args.json:
        print(json.dumps(render_json(task_dir, checks), indent=2, sort_keys=True))
    else:
        print(render_text(task_dir, checks, errors_only=args.errors_only))

    failure_checks = init_checks if args.init_layout and not args.init_runtime_product else checks
    has_failures = any(check.status == "FAIL" for check in failure_checks)
    strict_warning_checks = []
    if args.strict_warnings:
        strict_warning_checks = _strict_warning_checks(
            checks,
            explicit_flags=_strict_warning_explicit_flags(args),
        )
    if has_failures or (args.strict_warnings and strict_warning_checks):
        return 1
    return 0


def _strict_warning_explicit_flags(args: argparse.Namespace) -> set[str]:
    flags: set[str] = set()
    for flag in ("runtime_product", "xen_runtime", "init_runtime_product", "run_env_check"):
        if getattr(args, flag, False):
            flags.add(flag)
    return flags


def _strict_warning_checks(checks: list[Check], *, explicit_flags: set[str]) -> list[Check]:
    non_strict_warnings = _load_non_strict_warning_policy()
    strict_checks: list[Check] = []
    for check in checks:
        if check.status != "WARN":
            continue
        policy = non_strict_warnings.get(check.code)
        if policy is None or policy.intersection(explicit_flags):
            strict_checks.append(check)
    return strict_checks


def _load_non_strict_warning_policy() -> dict[str, set[str]]:
    data = yaml.safe_load(WARNING_POLICY_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{WARNING_POLICY_FILE} must contain a mapping")
    entries = data.get("non_strict_warnings", {})
    if not isinstance(entries, dict):
        raise ValueError("warning policy non_strict_warnings must be a mapping")

    policy: dict[str, set[str]] = {}
    for code, entry in entries.items():
        if not isinstance(code, str) or not isinstance(entry, dict):
            raise ValueError("warning policy entries must map warning codes to objects")
        strict_when_flags = entry.get("strict_when_flags", [])
        if not isinstance(strict_when_flags, list) or not all(isinstance(flag, str) for flag in strict_when_flags):
            raise ValueError(f"warning policy {code} strict_when_flags must be a string list")
        policy[code] = set(strict_when_flags)
    return policy


def check_task(
    task_dir: Path,
    *,
    workspace: Path,
    require_runtime_product: bool = False,
    require_xen_runtime: bool = False,
) -> list[Check]:
    checks: list[Check] = []

    checks.append(_check_task_dir(task_dir, workspace))
    if not task_dir.exists() or not task_dir.is_dir():
        return checks

    checks.extend(_check_layout(task_dir))
    checks.extend(_check_legacy_task_context_markdown(task_dir))
    slots, context_text = _load_task_context(task_dir, checks)
    if any(check.status == "PASS" and check.code == "task-context-database-valid" for check in checks):
        checks.extend(_check_task_context_quality(task_dir, slots))

    manifests = _find_artifact_manifests(task_dir)
    harness_profiles = _find_xen_zephyr_harness_profiles(task_dir)

    has_runtime_hints = _has_runtime_hints(context_text)
    should_check_manifest = require_runtime_product or has_runtime_hints or bool(manifests) or bool(harness_profiles)
    should_check_scenarios = require_xen_runtime or bool(harness_profiles) or _has_xen_hints(context_text)

    if should_check_manifest:
        checks.extend(_check_artifact_manifests(task_dir, manifests))
    else:
        checks.append(
            Check(
                "PASS",
                "artifact-manifest-not-required",
                "no runtime product hints found; artifact manifest check skipped",
                str(task_dir / "dev"),
            )
        )

    if should_check_scenarios:
        checks.extend(_check_harness_profiles(task_dir, harness_profiles, manifests))
    else:
        checks.append(
            Check(
                "PASS",
                "xen-runtime-not-required",
                "no Xen/QEMU runtime hints found; runtime YAML check skipped",
                str(task_dir / "scripts"),
            )
        )

    return checks


def initialize_task_layout(task_dir: Path, *, workspace: Path, privacy: str = "public") -> list[Check]:
    checks: list[Check] = []
    try:
        task_dir.relative_to(workspace)
    except ValueError:
        return [Check("FAIL", "init-outside-workspace", "refusing to initialize task outside workspace", str(task_dir))]

    task_dir.mkdir(parents=True, exist_ok=True)
    checks.append(Check("PASS", "init-task-dir", "task directory is present", str(task_dir)))

    for rel_path in REQUIRED_DIRS:
        path = task_dir / rel_path
        if path.exists() and not path.is_dir():
            checks.append(
                Check(
                    "FAIL",
                    "init-path-not-directory",
                    f"path exists but is not a directory: {rel_path}",
                    str(path),
                )
            )
            continue
        path.mkdir(parents=True, exist_ok=True)
        checks.append(Check("PASS", "init-layout-dir", f"directory is present: {rel_path}", str(path)))

    database_path = task_dir / TASK_CONTEXT_DATABASE_FILE
    if database_path.exists():
        checks.append(Check("PASS", "init-task-context-database-existing", f"{TASK_CONTEXT_DATABASE_FILE} already exists", str(database_path)))
    else:
        ensure_task_context_database(task_dir)
        checks.append(Check("PASS", "init-task-context-database", f"created {TASK_CONTEXT_DATABASE_FILE}", str(database_path)))

    metadata_path = task_dir / TASK_METADATA_FILE
    if metadata_path.exists():
        checks.append(Check("PASS", "init-task-metadata-existing", f"{TASK_METADATA_FILE} already exists", str(metadata_path)))
    else:
        metadata = {
            "privacy": privacy,
        }
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        checks.append(Check("PASS", "init-task-metadata", f"created {TASK_METADATA_FILE}", str(metadata_path)))

    for result in actualize_task(task_dir, workspace=workspace):
        checks.append(Check(result.status, result.code, result.message, result.path))

    return checks


def initialize_runtime_product(task_dir: Path, *, workspace: Path) -> list[Check]:
    checks: list[Check] = []
    try:
        task_dir.relative_to(workspace)
    except ValueError:
        return [
            Check(
                "FAIL",
                "init-runtime-outside-workspace",
                "refusing to initialize runtime product outside workspace",
                str(task_dir),
            )
        ]

    runtime_report_dir = task_dir / "report" / "runtime"
    runtime_report_dir.mkdir(parents=True, exist_ok=True)
    checks.append(Check("PASS", "init-runtime-dir", "runtime report directory is present", str(runtime_report_dir)))

    manifest_path = task_dir / "dev" / "product-artifacts.yaml"
    if manifest_path.exists():
        checks.append(Check("PASS", "init-artifact-manifest-existing", "artifact manifest already exists", str(manifest_path)))
    else:
        template = PRODUCT_ARTIFACTS_TEMPLATE.read_text(encoding="utf-8")
        manifest_path.write_text(template, encoding="utf-8")
        checks.append(Check("PASS", "init-artifact-manifest", "created product artifact manifest", str(manifest_path)))

    scenario_dir = task_dir / "scripts" / "paf"
    scenario_dir.mkdir(parents=True, exist_ok=True)
    checks.append(Check("PASS", "init-xen-runtime-yaml-dir", "PAF runtime profile directory is present", str(scenario_dir)))

    scenario_path = scenario_dir / DEFAULT_RUNTIME_YAML_NAME
    if scenario_path.exists():
        checks.append(Check("PASS", "init-xen-runtime-yaml-existing", "starter runtime YAML already exists", str(scenario_path)))
    else:
        scenario_path.write_text(_starter_scenario_text(), encoding="utf-8")
        checks.append(Check("PASS", "init-xen-runtime-yaml", "created starter Xen/Zephyr runtime YAML", str(scenario_path)))

    return checks


def check_environment_commands(task_dir: Path, *, workspace: Path, run: bool) -> list[Check]:
    harness_profiles = _find_xen_zephyr_harness_profiles(task_dir)
    if not _uses_environment_domain(harness_profiles):
        return [
            Check(
                "WARN",
                "environment-check-none",
                "no environments domain usage found from Xen/Zephyr runtime YAML",
                str(task_dir / "scripts"),
            )
        ]

    command = [
        "agent_tools/paf_workspace/run-paf.sh",
        "agent_tools/paf_workspace/domains/environments/scenarios/zephyr-xen.xml",
        "check-only",
        "--yaml-config",
        "agent_tools/paf_workspace/domains/environments/profiles/zephyr-xen.yaml",
    ]
    command_text = " ".join(command)
    checks = [
        Check(
            "PASS",
            "environment-check-command",
            f"run: {command_text}",
            str(workspace / "agent_tools/paf_workspace/domains/environments/scenarios/zephyr-xen.xml"),
        )
    ]
    if run:
        checks.append(_run_environment_check(workspace, command))
    return checks


def render_json(task_dir: Path, checks: list[Check]) -> dict[str, Any]:
    counts = _counts(checks)
    return {
        "task_dir": str(task_dir),
        "summary": counts,
        "checks": [check.as_dict() for check in checks],
    }


def render_text(task_dir: Path, checks: list[Check], *, errors_only: bool = False) -> str:
    lines = [f"Task check: {task_dir}"]
    counts = _counts(checks)
    lines.append(f"Summary: {counts['PASS']} pass, {counts['WARN']} warn, {counts['FAIL']} fail")
    for check in checks:
        if errors_only and check.status != "FAIL":
            continue
        suffix = f" ({check.path})" if check.path else ""
        lines.append(f"{check.status} {check.code}: {check.message}{suffix}")
    return "\n".join(lines)


def _resolve_task_dir(workspace: Path, task_dir: str) -> Path:
    path = Path(task_dir)
    if path.is_absolute():
        return path.resolve()
    if len(path.parts) == 1:
        return (workspace / TASKS_DIR_NAME / path).resolve()
    return (workspace / path).resolve()


def _check_task_dir(task_dir: Path, workspace: Path) -> Check:
    if not task_dir.exists():
        return Check("FAIL", "task-dir-missing", "task directory does not exist", str(task_dir))
    if not task_dir.is_dir():
        return Check("FAIL", "task-dir-not-directory", "task path is not a directory", str(task_dir))
    try:
        task_dir.relative_to(workspace)
    except ValueError:
        return Check("FAIL", "task-outside-workspace", "task directory is outside workspace root", str(task_dir))
    tasks_root = workspace / TASKS_DIR_NAME
    try:
        task_dir.relative_to(tasks_root)
    except ValueError:
        return Check("FAIL", "task-outside-tasks", "task directory must be under tasks/", str(task_dir))
    if task_dir.parent != tasks_root:
        return Check("FAIL", "task-not-top-level", "task directory is not directly under tasks/", str(task_dir))
    return Check("PASS", "task-dir", "task directory exists", str(task_dir))


def _check_layout(task_dir: Path) -> list[Check]:
    checks: list[Check] = []
    for rel_path in REQUIRED_DIRS:
        path = task_dir / rel_path
        if path.is_dir():
            checks.append(Check("PASS", "layout-dir", f"required directory exists: {rel_path}", str(path)))
        else:
            checks.append(Check("FAIL", "layout-dir-missing", f"required directory is missing: {rel_path}", str(path)))
    return checks


def _check_legacy_task_context_markdown(task_dir: Path) -> list[Check]:
    path = task_dir / "TASK_CONTEXT.md"
    if not path.exists():
        return []
    if not path.is_file():
        return [Check("FAIL", "task-context-markdown-not-file", "legacy TASK_CONTEXT.md path is not a file", str(path))]
    return [
        Check(
            "WARN",
            "task-context-markdown-legacy",
            "legacy TASK_CONTEXT.md is imported into TASK_CONTEXT.sqlite3 legacy slot and should be removed",
            str(path),
        )
    ]


def _load_task_context(task_dir: Path, checks: list[Check]) -> tuple[list[TaskContextSlot], str]:
    database_path = task_dir / TASK_CONTEXT_DATABASE_FILE
    if not database_path.exists():
        ensure_task_context_database(task_dir)
    checks.append(Check("PASS", "task-context-database", f"{TASK_CONTEXT_DATABASE_FILE} exists", str(database_path)))
    with database_path.open("rb") as database_file:
        database_header = database_file.read(16)
    if database_path.stat().st_size > 0 and database_header != b"SQLite format 3\x00":
        checks.append(
            Check(
                "FAIL",
                "task-context-database-invalid",
                f"{TASK_CONTEXT_DATABASE_FILE} is not a SQLite database",
                str(database_path),
            )
        )
        return [], ""
    try:
        slots = load_task_context_slots(task_dir)
        checks.append(Check("PASS", "task-context-database-valid", f"{TASK_CONTEXT_DATABASE_FILE} is valid", str(database_path)))
        return slots, _task_context_search_text(slots)
    except (ValueError, OSError, sqlite3.DatabaseError) as exc:
        checks.append(Check("FAIL", "task-context-database-invalid", str(exc), str(database_path)))
        return [], ""


def _task_context_search_text(slots: list[TaskContextSlot]) -> str:
    return "\n".join(slot.content for slot in slots if slot.content)


def _check_task_context_quality(task_dir: Path, slots: list[TaskContextSlot]) -> list[Check]:
    checks: list[Check] = []
    by_category = {slot.category: slot for slot in slots}
    unknown = sorted(category for category in by_category if category not in SLOT_CATEGORIES)
    if unknown:
        checks.append(
            Check(
                "FAIL",
                "task-context-slot-category",
                f"unknown task context slot categories: {', '.join(unknown)}",
                str(task_dir / TASK_CONTEXT_DATABASE_FILE),
            )
        )
    for category in REQUIRED_SLOT_CATEGORIES:
        slot = by_category.get(category)
        if slot is None or not slot.content.strip():
            checks.append(
                Check(
                    "FAIL",
                    "task-context-slot-required",
                    f"required task context slot is missing or empty: {category}",
                    str(task_dir / TASK_CONTEXT_DATABASE_FILE),
                )
            )
        else:
            checks.append(
                Check(
                    "PASS",
                    "task-context-slot-required",
                    f"required task context slot is present: {category}",
                    str(task_dir / TASK_CONTEXT_DATABASE_FILE),
                )
            )
    for category in RECOMMENDED_SLOT_CATEGORIES:
        slot = by_category.get(category)
        if slot is None or not slot.content.strip():
            checks.append(
                Check(
                    "WARN",
                    "task-context-slot-recommended",
                    f"recommended task context slot is missing or empty: {category}",
                    str(task_dir / TASK_CONTEXT_DATABASE_FILE),
                )
            )
        else:
            checks.append(
                Check(
                    "PASS",
                    "task-context-slot-recommended",
                    f"recommended task context slot is present: {category}",
                    str(task_dir / TASK_CONTEXT_DATABASE_FILE),
                )
            )
    legacy = by_category.get("legacy")
    if legacy is not None and legacy.content.strip():
        checks.append(
            Check(
                "FAIL",
                "task-context-slot-legacy",
                "legacy task context slot is non-empty; move current facts into typed slots",
                str(task_dir / TASK_CONTEXT_DATABASE_FILE),
            )
        )
    slot_tokens = _rough_token_count(_task_context_search_text(slots))
    if slot_tokens > TASK_CONTEXT_ACTIVE_TOKEN_BUDGET:
        checks.append(
            Check(
                "FAIL",
                "task-context-slots-size",
                f"task context slots are too large: ~{slot_tokens} tokens, budget {TASK_CONTEXT_ACTIVE_TOKEN_BUDGET}",
                str(task_dir / TASK_CONTEXT_DATABASE_FILE),
            )
        )
    else:
        checks.append(
            Check(
                "PASS",
                "task-context-slots-size",
                f"task context slots fit the budget: ~{slot_tokens}/{TASK_CONTEXT_ACTIVE_TOKEN_BUDGET} tokens",
                str(task_dir / TASK_CONTEXT_DATABASE_FILE),
            )
        )
    return checks


def _rough_token_count(text: str) -> int:
    lexical_tokens = len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))
    char_tokens = (len(text) + 3) // 4
    return max(lexical_tokens, char_tokens)


def _check_artifact_manifests(task_dir: Path, manifests: list[Path]) -> list[Check]:
    if not manifests:
        return [
            Check(
                "WARN",
                "artifact-manifest-missing",
                "no task-owned product-artifacts.yaml found under dev/ or dev/*/",
                str(task_dir / "dev"),
            )
        ]

    checks: list[Check] = []
    required_tokens = ("product:", "artifacts:", "domains:", "validation:")
    for manifest in manifests:
        text = manifest.read_text(encoding="utf-8")
        missing = [token for token in required_tokens if token not in text]
        if missing:
            checks.append(
                Check(
                    "WARN",
                    "artifact-manifest-incomplete",
                    "artifact manifest is missing sections: " + ", ".join(missing),
                    str(manifest),
                )
            )
        else:
            checks.append(Check("PASS", "artifact-manifest", "artifact manifest has core sections", str(manifest)))
    return checks


def _find_artifact_manifests(task_dir: Path) -> list[Path]:
    dev_dir = task_dir / "dev"
    if not dev_dir.exists():
        return []
    manifests: list[Path] = []
    for path in _task_owned_manifest_candidates(dev_dir):
        if _is_inside_nested_repo(path, dev_dir):
            continue
        if path.is_file():
            manifests.append(path)
    return sorted(manifests)


def _task_owned_manifest_candidates(dev_dir: Path) -> list[Path]:
    candidates = [dev_dir / "product-artifacts.yaml"]
    try:
        children = list(dev_dir.iterdir())
    except OSError:
        return candidates
    for child in children:
        if not child.is_dir():
            continue
        if (child / ".git").exists():
            continue
        candidates.append(child / "product-artifacts.yaml")
    return candidates


def _is_inside_nested_repo(path: Path, root: Path) -> bool:
    for parent in path.parents:
        if parent == root:
            return False
        if (parent / ".git").exists():
            return True
    return False


def _find_xen_zephyr_harness_profiles(task_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    root = task_dir / "scripts"
    if not root.exists():
        return []
    candidates.extend(root.rglob("*.yaml"))
    candidates.extend(root.rglob("*.yml"))
    return [path for path in sorted(candidates) if _yaml_has_xen_zephyr_harness(path)]


def _yaml_has_xen_zephyr_harness(path: Path) -> bool:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return isinstance(data, dict) and isinstance(data.get("xen_zephyr"), dict) and isinstance(
        data["xen_zephyr"].get("harness"),
        dict,
    )


def _check_harness_profiles(
    task_dir: Path,
    profiles: list[Path],
    manifests: list[Path],
) -> list[Check]:
    if not profiles:
        return [
            Check(
                "WARN",
                "xen-runtime-yaml-missing",
                "no scripts/**/*.yaml with xen_zephyr.harness found; required for Xen/QEMU runtime validation",
                str(task_dir / "scripts"),
            )
        ]

    checks: list[Check] = []
    for profile in profiles:
        try:
            data = yaml.safe_load(profile.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            checks.append(Check("FAIL", "xen-runtime-yaml", f"runtime YAML is invalid: {error}", str(profile)))
            continue

        checks.extend(_check_runtime_yaml_fields(profile, data))

    if not manifests:
        checks.append(
            Check(
                "WARN",
                "xen-runtime-without-manifest",
                "Xen runtime YAML exists but no product artifact manifest was found",
                str(task_dir / "dev"),
            )
        )
    return checks


def _check_runtime_yaml_fields(profile: Path, data: Any) -> list[Check]:
    if not isinstance(data, dict):
        return [Check("FAIL", "xen-runtime-yaml-shape", "runtime YAML root must be an object", str(profile))]

    xen_zephyr = data.get("xen_zephyr")
    if not isinstance(xen_zephyr, dict):
        return [Check("FAIL", "xen-runtime-yaml-domain", "missing xen_zephyr object", str(profile))]

    harness = xen_zephyr.get("harness")
    if not isinstance(harness, dict):
        return [Check("FAIL", "xen-runtime-yaml-harness", "missing xen_zephyr.harness object", str(profile))]

    checks: list[Check] = []
    recommended_fields = ("name", "preset", "dom0_bin", "domu_bin", "expect", "log_file")
    for field in recommended_fields:
        if field in harness:
            checks.append(Check("PASS", "xen-runtime-yaml-field", f"harness field present: {field}", str(profile)))
        else:
            checks.append(Check("WARN", "xen-runtime-yaml-field-missing", f"harness field missing: {field}", str(profile)))

    return checks


def _check_artifact_paths(scenario: Path, workspace: Path, artifacts: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    for label in ("xen", "qemu", "dom0"):
        checks.extend(_check_optional_path(workspace, artifacts.get(label), f"artifacts.{label}", scenario))

    domus = artifacts.get("domus")
    if isinstance(domus, list):
        for index, domu in enumerate(domus):
            if isinstance(domu, dict):
                checks.extend(_check_optional_path(workspace, domu.get("image"), f"artifacts.domus[{index}].image", scenario))
    return checks


def _check_optional_path(workspace: Path, value: Any, label: str, source_path: Path) -> list[Check]:
    if not isinstance(value, str) or not value or _is_placeholder(value):
        return [Check("PASS", "artifact-path-placeholder", f"artifact path not filled yet: {label}", str(source_path))]

    path = Path(value)
    if not path.is_absolute():
        path = workspace / path
    path = path.resolve()
    if path.exists():
        return [Check("PASS", "artifact-path", f"artifact path exists: {label}", str(path))]
    return [Check("WARN", "artifact-path-missing", f"artifact path is filled but missing: {label}={value}", str(source_path))]


def _uses_environment_domain(profiles: list[Path]) -> bool:
    for profile in profiles:
        try:
            data = yaml.safe_load(profile.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        uses = data.get("uses")
        if isinstance(uses, list):
            for entry in uses:
                if isinstance(entry, dict) and entry.get("domain") == "environments":
                    return True
        case = data.get("case")
        if isinstance(case, dict) and case.get("domain") == "environments":
            return True
    return False


def _run_environment_check(workspace: Path, command: list[str]) -> Check:
    try:
        completed = subprocess.run(
            command,
            cwd=workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return Check("WARN", "environment-check-timeout", "PAF environment check timed out after 120 seconds")
    except OSError as error:
        return Check("WARN", "environment-check-error", f"could not run PAF environment check: {error}")
    output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    summary = _first_line(output) or "no output"
    if completed.returncode == 0:
        return Check("PASS", "environment-check-run", f"PAF environment check passed: {summary}")
    return Check("WARN", "environment-check-run-failed", f"PAF environment check failed ({completed.returncode}): {summary}")


def _first_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _is_placeholder(value: str) -> bool:
    stripped = value.strip()
    return stripped.startswith("<") or "<" in stripped or stripped in {".", "-"}


def _has_runtime_hints(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in RUNTIME_HINTS)


def _has_xen_hints(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in ("xen", "qemu", "dom0", "domu", "hypervisor"))


def _starter_scenario_text() -> str:
    return """case:
  name: task-xen-zephyr-runtime
  domain: xen-zephyr

xen_zephyr:
  harness:
    name: scenario-name
    preset: zephyr-xen-qemu
    log_file: report/runtime/scenario-name.log
    timeout_sec: 30
    dom0_bin: dev/product/dom0/zephyr.bin
    domu_bin: dev/product/domu/zephyr.bin
    expect:
      - source: xen
        text: ""
      - source: domu1
        text: ""
    require_source:
      - xen
      - dom0
      - domu1
"""


def _counts(checks: list[Check]) -> dict[str, int]:
    return {
        "PASS": sum(1 for check in checks if check.status == "PASS"),
        "WARN": sum(1 for check in checks if check.status == "WARN"),
        "FAIL": sum(1 for check in checks if check.status == "FAIL"),
    }

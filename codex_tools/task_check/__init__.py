from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REQUIRED_DIRS = ("dev", "Dockerfile", "scripts", "report", "report/diff", "report/puml")
ENVIRONMENT_FILES = (
    "Dockerfile",
    "README.md",
    "scripts/check.sh",
    "scripts/build.sh",
    "scripts/run.sh",
    "scripts/validate.sh",
)
TASK_CONTEXT_SECTIONS = (
    "## Goal",
    "## Repositories",
    "## Environment",
    "## Knowledge",
    "## Build/Product",
    "## Validation Status",
    "## Tool Failures",
    "## Decisions",
    "## Blockers",
    "## Next Steps",
)
VALIDATION_LEVELS = ("static", "build", "runtime", "review")
RUNTIME_HINTS = ("xen", "qemu", "moulin", "dom0", "domu", "hypervisor")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TASK_CONTEXT_TEMPLATE = PROJECT_ROOT / "codex_tools" / "templates" / "TASK_CONTEXT.md"
PRODUCT_ARTIFACTS_TEMPLATE = PROJECT_ROOT / "codex_tools" / "templates" / "product-artifacts.yaml"
DEFAULT_RUNTIME_YAML_NAME = "xen-zephyr-runtime.yaml"


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
        help="Create missing task directories and TASK_CONTEXT.md from the workspace template.",
    )
    parser.add_argument(
        "--init-runtime-product",
        action="store_true",
        help="Create runtime product manifest, Xen scenario directory, starter scenario, and runtime report directory.",
    )
    parser.add_argument(
        "--env-check-command",
        action="store_true",
        help="Print discovered environment check.sh commands without running them.",
    )
    parser.add_argument(
        "--run-env-check",
        action="store_true",
        help="Run discovered environment check.sh commands. This does not build images.",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    workspace = Path(args.workspace).resolve()
    task_dir = _resolve_task_dir(workspace, args.task_dir)
    init_checks: list[Check] = []
    if args.init_layout or args.init_runtime_product:
        init_checks = initialize_task_layout(task_dir, workspace=workspace)
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
        print(render_text(task_dir, checks))

    has_failures = any(check.status == "FAIL" for check in checks)
    has_warnings = any(check.status == "WARN" for check in checks)
    if has_failures or (args.strict_warnings and has_warnings):
        return 1
    return 0


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
    context_text = _read_task_context(task_dir, checks)
    if context_text is not None:
        checks.extend(_check_task_context(task_dir, context_text))

    manifests = sorted((task_dir / "dev").rglob("product-artifacts.yaml")) if (task_dir / "dev").exists() else []
    harness_profiles = _find_xen_zephyr_harness_profiles(task_dir)

    has_runtime_hints = _has_runtime_hints(context_text or "")
    should_check_manifest = require_runtime_product or has_runtime_hints or bool(manifests) or bool(harness_profiles)
    should_check_scenarios = require_xen_runtime or bool(harness_profiles) or _has_xen_hints(context_text or "")

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


def initialize_task_layout(task_dir: Path, *, workspace: Path) -> list[Check]:
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
            checks.append(Check("FAIL", "init-path-not-directory", f"path exists but is not a directory: {rel_path}", str(path)))
            continue
        path.mkdir(parents=True, exist_ok=True)
        checks.append(Check("PASS", "init-layout-dir", f"directory is present: {rel_path}", str(path)))

    context_path = task_dir / "TASK_CONTEXT.md"
    if context_path.exists():
        checks.append(Check("PASS", "init-task-context-existing", "TASK_CONTEXT.md already exists", str(context_path)))
    else:
        template = TASK_CONTEXT_TEMPLATE.read_text(encoding="utf-8")
        context_path.write_text(template, encoding="utf-8")
        checks.append(Check("PASS", "init-task-context", "created TASK_CONTEXT.md from template", str(context_path)))

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
    environment_paths = _scenario_environment_paths(harness_profiles, workspace)
    if not environment_paths:
        return [
            Check(
                "WARN",
                "environment-check-none",
                "no environment check commands found from Xen/Zephyr runtime YAML",
                str(task_dir / "scripts"),
            )
        ]

    checks: list[Check] = []
    for environment_path in environment_paths:
        check_script = environment_path / "scripts" / "check.sh"
        if not check_script.exists():
            checks.append(Check("WARN", "environment-check-missing", "environment check.sh is missing", str(check_script)))
            continue
        command = str(check_script)
        checks.append(Check("PASS", "environment-check-command", f"run: {command}", str(check_script)))
        if run:
            checks.append(_run_environment_check(check_script))
    return checks


def render_json(task_dir: Path, checks: list[Check]) -> dict[str, Any]:
    counts = _counts(checks)
    return {
        "task_dir": str(task_dir),
        "summary": counts,
        "checks": [check.as_dict() for check in checks],
    }


def render_text(task_dir: Path, checks: list[Check]) -> str:
    lines = [f"Task check: {task_dir}"]
    counts = _counts(checks)
    lines.append(f"Summary: {counts['PASS']} pass, {counts['WARN']} warn, {counts['FAIL']} fail")
    for check in checks:
        suffix = f" ({check.path})" if check.path else ""
        lines.append(f"{check.status} {check.code}: {check.message}{suffix}")
    return "\n".join(lines)


def _resolve_task_dir(workspace: Path, task_dir: str) -> Path:
    path = Path(task_dir)
    if not path.is_absolute():
        path = workspace / path
    return path.resolve()


def _check_task_dir(task_dir: Path, workspace: Path) -> Check:
    if not task_dir.exists():
        return Check("FAIL", "task-dir-missing", "task directory does not exist", str(task_dir))
    if not task_dir.is_dir():
        return Check("FAIL", "task-dir-not-directory", "task path is not a directory", str(task_dir))
    try:
        task_dir.relative_to(workspace)
    except ValueError:
        return Check("WARN", "task-outside-workspace", "task directory is outside workspace root", str(task_dir))
    if task_dir.parent != workspace:
        return Check("WARN", "task-not-top-level", "task directory is not directly under workspace root", str(task_dir))
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


def _read_task_context(task_dir: Path, checks: list[Check]) -> str | None:
    path = task_dir / "TASK_CONTEXT.md"
    if not path.exists():
        checks.append(Check("FAIL", "task-context-missing", "TASK_CONTEXT.md is missing", str(path)))
        return None
    if not path.is_file():
        checks.append(Check("FAIL", "task-context-not-file", "TASK_CONTEXT.md is not a file", str(path)))
        return None
    text = path.read_text(encoding="utf-8")
    checks.append(Check("PASS", "task-context", "TASK_CONTEXT.md exists", str(path)))
    return text


def _check_task_context(task_dir: Path, text: str) -> list[Check]:
    checks: list[Check] = []
    context_path = str(task_dir / "TASK_CONTEXT.md")
    for section in TASK_CONTEXT_SECTIONS:
        if section in text:
            checks.append(Check("PASS", "task-context-section", f"section present: {section}", context_path))
        else:
            checks.append(Check("WARN", "task-context-section-missing", f"section missing: {section}", context_path))

    for level in VALIDATION_LEVELS:
        if level in text:
            checks.append(Check("PASS", "validation-level", f"validation level mentioned: {level}", context_path))
        else:
            checks.append(Check("WARN", "validation-level-missing", f"validation level missing: {level}", context_path))
    return checks


def _check_artifact_manifests(task_dir: Path, manifests: list[Path]) -> list[Check]:
    if not manifests:
        return [
            Check(
                "WARN",
                "artifact-manifest-missing",
                "no dev/**/product-artifacts.yaml found; required for multi-artifact runtime products",
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


def _find_xen_zephyr_harness_profiles(task_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for root in (task_dir / "scripts", task_dir / "dev"):
        if not root.exists():
            continue
        candidates.extend(root.rglob("*.yaml"))
        candidates.extend(root.rglob("*.yml"))
    return [path for path in sorted(candidates) if _yaml_has_xen_zephyr_harness(path)]


def _yaml_has_xen_zephyr_harness(path: Path) -> bool:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
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


def _check_environment_path(workspace: Path, environment: str, source_path: Path) -> list[Check]:
    environment_path = Path(environment)
    if not environment_path.is_absolute():
        environment_path = workspace / environment_path
    environment_path = environment_path.resolve()

    if not environment_path.exists():
        return [
            Check(
                "WARN",
                "environment-missing",
                f"referenced environment does not exist: {environment}",
                str(source_path),
            )
        ]
    if not environment_path.is_dir():
        return [
            Check(
                "WARN",
                "environment-not-directory",
                f"referenced environment is not a directory: {environment}",
                str(environment_path),
            )
        ]

    checks = [Check("PASS", "environment", f"referenced environment exists: {environment}", str(environment_path))]
    for rel_path in ENVIRONMENT_FILES:
        path = environment_path / rel_path
        if path.exists():
            checks.append(Check("PASS", "environment-file", f"environment file exists: {rel_path}", str(path)))
        else:
            checks.append(Check("WARN", "environment-file-missing", f"environment file missing: {rel_path}", str(path)))
    return checks


def _scenario_environment_paths(profiles: list[Path], workspace: Path) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for profile in profiles:
        try:
            data = yaml.safe_load(profile.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        docker = data.get("docker")
        if not isinstance(docker, dict):
            continue
        images = docker.get("images")
        if not isinstance(images, dict):
            continue
        image = images.get("zephyr-xen")
        if not isinstance(image, dict):
            continue
        environment = image.get("context")
        if not isinstance(environment, str) or not environment:
            continue
        path = Path(environment)
        if not path.is_absolute():
            path = workspace / path
        path = path.resolve()
        if path not in seen:
            paths.append(path)
            seen.add(path)
    return paths


def _run_environment_check(check_script: Path) -> Check:
    try:
        completed = subprocess.run(
            [str(check_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return Check("WARN", "environment-check-timeout", "check.sh timed out after 120 seconds", str(check_script))
    except OSError as error:
        return Check("WARN", "environment-check-error", f"could not run check.sh: {error}", str(check_script))
    output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    summary = _first_line(output) or "no output"
    if completed.returncode == 0:
        return Check("PASS", "environment-check-run", f"check.sh passed: {summary}", str(check_script))
    return Check("WARN", "environment-check-run-failed", f"check.sh failed ({completed.returncode}): {summary}", str(check_script))


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

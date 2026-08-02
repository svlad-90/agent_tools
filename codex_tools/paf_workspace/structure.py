"""Structural checks for the workspace PAF layout."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree


REQUIRED_DOMAIN_FILES = ("README.md", "__init__.py", "domain.yaml", "schema.yaml")
REQUIRED_DOMAIN_DIRS = ("lib", "scenarios", "profiles")


class StructureIssue:
    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        self.message = message

    def format(self, root: Path) -> str:
        try:
            display_path = self.path.relative_to(root)
        except ValueError:
            display_path = self.path
        return f"{display_path}: {self.message}"


def _is_python_package_name(value: str) -> bool:
    return value.isidentifier() and "-" not in value


def _check_domain(root: Path, domain: Path) -> list[StructureIssue]:
    issues: list[StructureIssue] = []
    if not _is_python_package_name(domain.name):
        issues.append(
            StructureIssue(
                domain,
                "domain directory must be a Python package name; keep hyphenated public names in domain.yaml",
            )
        )

    for filename in REQUIRED_DOMAIN_FILES:
        if not (domain / filename).is_file():
            issues.append(StructureIssue(domain / filename, "missing required domain file"))

    tasks_file = domain / "tasks.py"
    tasks_package = domain / "tasks" / "__init__.py"
    if tasks_file.exists() and tasks_package.exists():
        issues.append(StructureIssue(domain / "tasks", "domain must not define both tasks.py and tasks/ package"))
    if not tasks_file.is_file() and not tasks_package.is_file():
        issues.append(StructureIssue(domain / "tasks.py", "missing tasks.py or tasks/__init__.py entry point"))

    for dirname in REQUIRED_DOMAIN_DIRS:
        if not (domain / dirname).is_dir():
            issues.append(StructureIssue(domain / dirname, "missing required domain directory"))

    if (domain / "lib").is_dir() and not (domain / "lib" / "__init__.py").is_file():
        issues.append(StructureIssue(domain / "lib" / "__init__.py", "domain lib must be a Python package"))

    for forbidden in ("harness", "templates/profile", "templates/profiles"):
        if (domain / forbidden).exists():
            issues.append(StructureIssue(domain / forbidden, "unsupported domain support directory"))

    for dockerfile in domain.glob("assets/*/Dockerfile"):
        readme = dockerfile.parent / "README.md"
        if not readme.is_file():
            issues.append(StructureIssue(readme, "Dockerfile asset must have a README.md"))

        asset_name = dockerfile.parent.name
        if domain.name == "environments":
            scenario = domain / "scenarios" / f"{asset_name}.xml"
            profile = domain / "profiles" / f"{asset_name}.yaml"
            if not scenario.is_file():
                issues.append(StructureIssue(scenario, "environment asset must have a matching scenario XML"))
            if not profile.is_file():
                issues.append(StructureIssue(profile, "environment asset must have a matching profile YAML"))

    if domain.name == "environments":
        for shell_script in domain.glob("assets/**/*.sh"):
            issues.append(StructureIssue(shell_script, "environment domain assets must not expose shell scripts"))

    for scenario in domain.glob("scenarios/*.xml"):
        try:
            ElementTree.parse(scenario)
        except ElementTree.ParseError as error:
            issues.append(StructureIssue(scenario, f"scenario XML is not well-formed: {error}"))

    for py_file in domain.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        text = py_file.read_text(encoding="utf-8")
        if "import_module(" in text:
            issues.append(StructureIssue(py_file, "domain code must use static imports instead of import_module"))

    for old_task_module in domain.glob("*_tasks.py"):
        issues.append(StructureIssue(old_task_module, "split large task families into tasks/ package modules"))

    if tasks_package.is_file():
        text = tasks_package.read_text(encoding="utf-8")
        if "class " in text:
            issues.append(StructureIssue(tasks_package, "tasks package __init__.py must be compatibility exports only"))

    return issues


def check_paf_workspace_structure(root: Path) -> list[StructureIssue]:
    """Return structural issues for the workspace PAF layout."""

    root = root.resolve()
    issues: list[StructureIssue] = []
    workspace = root / "paf_workspace"
    domains = workspace / "domains"

    for required in (workspace / "run-paf.sh", workspace / "tasks.py", domains / "README.md"):
        if not required.is_file():
            issues.append(StructureIssue(required, "missing required PAF workspace file"))

    legacy_environments = root / "environments"
    if legacy_environments.exists():
        issues.append(StructureIssue(legacy_environments, "legacy environments must live in paf_workspace/domains/environments"))

    if not domains.is_dir():
        issues.append(StructureIssue(domains, "missing PAF domains directory"))
        return issues

    for domain in sorted(path for path in domains.iterdir() if path.is_dir() and not path.name.startswith("__")):
        issues.extend(_check_domain(root, domain))

    return issues


def assert_paf_workspace_structure(root: Path) -> None:
    issues = check_paf_workspace_structure(root)
    if issues:
        formatted = "\n".join(issue.format(root) for issue in issues)
        raise AssertionError(f"PAF workspace structure check failed:\n{formatted}")

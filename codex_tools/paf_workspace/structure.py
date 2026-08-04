"""Structural checks for codex_tools and the workspace PAF layout."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree


REQUIRED_DOMAIN_FILES = ("README.md", "__init__.py", "domain.yaml", "schema.yaml")
REQUIRED_DOMAIN_DIRS = ("lib", "scenarios", "profiles")
REQUIRED_CODEX_TOOLS_DIRS = ("knowledge", "paf_workspace", "rules", "skills", "tools")
ALLOWED_CODEX_TOOLS_DIRS = {
    *REQUIRED_CODEX_TOOLS_DIRS,
    ".cache",
    ".github",
    ".mypy_cache",
    ".pytest_cache",
}
FORBIDDEN_CODEX_TOOLS_DIRS = (
    "code_map",
    "commit_msg",
    "cpp_code_map",
    "diff_report",
    "environments",
    "moulin",
    "paf",
    "task_check",
    "templates",
    "yaml_map",
)
REQUIRED_TOOL_PACKAGES = ("code_map", "commit_msg", "cpp_code_map", "diff_report", "yaml_map")


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

    tasks_package = domain / "tasks" / "__init__.py"
    if not tasks_package.is_file():
        issues.append(StructureIssue(tasks_package, "missing required domain tasks package entry point"))
    if (domain / "tasks.py").exists():
        issues.append(StructureIssue(domain / "tasks.py", "domain PAF task entry point must be tasks/ package"))

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


def check_codex_tools_structure(root: Path) -> list[StructureIssue]:
    """Return structural issues for the codex_tools workspace layout."""

    root = root.resolve()
    issues: list[StructureIssue] = []

    for dirname in REQUIRED_CODEX_TOOLS_DIRS:
        if not (root / dirname).is_dir():
            issues.append(StructureIssue(root / dirname, "missing required codex_tools directory"))

    for dirname in FORBIDDEN_CODEX_TOOLS_DIRS:
        if (root / dirname).exists():
            issues.append(
                StructureIssue(root / dirname, "legacy codex_tools path must move into the owning namespace")
            )

    for path in sorted(root.iterdir()):
        if not path.is_dir() or path.name.startswith("."):
            continue
        if path.name not in ALLOWED_CODEX_TOOLS_DIRS:
            issues.append(StructureIssue(path, "unexpected top-level codex_tools directory"))

    tools = root / "tools"
    if tools.is_dir():
        if not (tools / "README.md").is_file():
            issues.append(StructureIssue(tools / "README.md", "missing tools directory README"))
        for tool_name in REQUIRED_TOOL_PACKAGES:
            tool = tools / tool_name
            if not (tool / "__init__.py").is_file():
                issues.append(StructureIssue(tool / "__init__.py", "missing tool package entry point"))
            if not (tool / "__main__.py").is_file():
                issues.append(StructureIssue(tool / "__main__.py", "missing tool CLI entry point"))

    if not (root / "paf_workspace" / "task_check" / "__main__.py").is_file():
        issues.append(StructureIssue(root / "paf_workspace" / "task_check", "missing PAF workspace task_check CLI"))
    task_context_template = root / "paf_workspace" / "templates" / "TASK_CONTEXT.md"
    product_artifacts_template = root / "paf_workspace" / "templates" / "product-artifacts.yaml"
    if not task_context_template.is_file():
        issues.append(StructureIssue(task_context_template, "missing task context template"))
    if not product_artifacts_template.is_file():
        issues.append(StructureIssue(product_artifacts_template, "missing product artifact template"))
    if (root / "knowledge" / "findings.md").exists():
        issues.append(StructureIssue(root / "knowledge" / "findings.md", "legacy findings pointer must move into knowledge/topics"))

    return issues


def assert_codex_tools_structure(root: Path) -> None:
    issues = check_codex_tools_structure(root)
    if issues:
        formatted = "\n".join(issue.format(root) for issue in issues)
        raise AssertionError(f"codex_tools structure check failed:\n{formatted}")


def assert_paf_workspace_structure(root: Path) -> None:
    issues = check_paf_workspace_structure(root)
    if issues:
        formatted = "\n".join(issue.format(root) for issue in issues)
        raise AssertionError(f"PAF workspace structure check failed:\n{formatted}")

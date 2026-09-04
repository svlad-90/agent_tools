from __future__ import annotations

from pathlib import Path

import yaml

from paf_workspace.domains.environments.lib.capabilities import CAPABILITY_REQUIREMENTS
from paf_workspace.domains.environments.lib.capabilities import normalize_capabilities
from paf_workspace.domains.environments.lib.capabilities import requirements_for_capabilities


AGENT_TOOLS_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = AGENT_TOOLS_ROOT.parent
DOMAIN_YAML = AGENT_TOOLS_ROOT / "paf_workspace/domains/environments/domain.yaml"


def test_all_declared_environment_images_have_known_capabilities() -> None:
    images = _environment_images()

    assert images
    for alias, config in images.items():
        capabilities = normalize_capabilities(config.get("capabilities"))
        assert "workspace_tools" in capabilities, f"{alias} must declare workspace_tools"
        assert set(capabilities) <= set(CAPABILITY_REQUIREMENTS), f"{alias} has unknown capabilities"


def test_environment_dockerfiles_include_capability_dependencies() -> None:
    images = _environment_images()
    for alias, config in images.items():
        capabilities = normalize_capabilities(config.get("capabilities"))
        requirements = requirements_for_capabilities(capabilities)
        source = "\n".join(_dockerfile_sources(alias, images))

        missing_apt = [package for package in requirements.apt_packages if not _has_token(source, package)]
        missing_pip = [package for package in requirements.pip_packages if not _has_token(source, package)]

        assert not missing_apt, f"{alias} Dockerfile is missing apt packages: {missing_apt}"
        assert not missing_pip, f"{alias} Dockerfile is missing pip packages: {missing_pip}"


def _environment_images() -> dict[str, dict[str, object]]:
    domain = yaml.safe_load(DOMAIN_YAML.read_text(encoding="utf-8"))
    images = domain["requires"]["images"]
    assert isinstance(images, dict)
    return images


def _dockerfile_sources(alias: str, images: dict[str, dict[str, object]]) -> list[str]:
    config = images[alias]
    dockerfile = WORKSPACE_ROOT / str(config["dockerfile"])
    source = dockerfile.read_text(encoding="utf-8")
    sources = [source]

    parent_alias = _parent_image_alias(source, images)
    if parent_alias:
        sources.extend(_dockerfile_sources(parent_alias, images))

    return sources


def _parent_image_alias(source: str, images: dict[str, dict[str, object]]) -> str | None:
    base_image = None
    for line in source.splitlines():
        if line.startswith("ARG BASE_IMAGE="):
            base_image = line.partition("=")[2].strip()
        if line.startswith("FROM "):
            from_value = line.split()[1]
            if from_value == "${BASE_IMAGE}":
                from_value = base_image or from_value
            for alias, config in images.items():
                if config.get("image") == from_value:
                    return alias
    return None


def _has_token(source: str, token: str) -> bool:
    normalized = source.replace("\\\n", "\n").replace("\t", " ")
    return any(token == part.strip() for part in normalized.replace(",", " ").split())

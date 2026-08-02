from __future__ import annotations

from pathlib import Path

import jsonschema
import yaml

from paf_workspace.structure import assert_paf_workspace_structure


def test_paf_workspace_structure() -> None:
    assert_paf_workspace_structure(Path(__file__).resolve().parents[2])


def test_environment_profiles_match_schema() -> None:
    codex_tools_root = Path(__file__).resolve().parents[2]
    environment_domain = codex_tools_root / "paf_workspace" / "domains" / "environments"
    schema = yaml.safe_load((environment_domain / "schema.yaml").read_text(encoding="utf-8"))

    for profile in sorted((environment_domain / "profiles").glob("*.yaml")):
        config = yaml.safe_load(profile.read_text(encoding="utf-8"))
        jsonschema.validate(config, schema)

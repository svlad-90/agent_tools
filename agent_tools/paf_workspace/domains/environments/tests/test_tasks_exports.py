from __future__ import annotations

import pytest


def test_run_container_command_is_exported_from_compat_module() -> None:
    pytest.importorskip("paf.paf_impl")
    from paf_workspace.domains.environments.tasks import run_container_command

    assert run_container_command.__name__ == "run_container_command"

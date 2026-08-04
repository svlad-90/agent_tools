"""Generic PAF tasks for running BitBake inside a Yocto workspace."""

from __future__ import annotations

import shlex
from pathlib import Path

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode

from codex_tools.tools.yocto_diag import DEFAULT_GRAPH_FILES
from codex_tools.tools.yocto_diag import GraphCopy
from codex_tools.tools.yocto_diag import YoctoInvocation
from codex_tools.tools.yocto_diag import bitbake_shell_command
from codex_tools.tools.yocto_diag import quote_words
from paf_workspace.tasks import WorkspaceTask


class YoctoTask(WorkspaceTask):
    """Base helper for running BitBake commands in a selected container."""

    def yocto_config(self) -> dict[str, object]:
        config = self.get_yaml_config().get("yocto", {})
        if isinstance(config, dict):
            return config
        return {}

    def yocto_string(self, key: str, default: str = "") -> str:
        value = self.yocto_config().get(key, default)
        return str(value) if value is not None else default

    def path_from_text(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return self.workspace_root() / path

    def container_alias(self) -> str:
        return (
            self.param("YOCTO_CONTAINER_ALIAS", "")
            or self.yocto_string("container")
            or "yocto-xen-workspace"
        )

    def yocto_dir(self) -> str:
        value = self.param("YOCTO_DIR", "") or ""
        if value:
            return value
        value = self.yocto_string("directory")
        if value:
            return value
        product_dir = self.param("PRODUCT_DIR", "") or ""
        if product_dir:
            return f"{product_dir}/yocto"
        self.fail("YOCTO_DIR or PRODUCT_DIR must be set")
        raise AssertionError("unreachable")

    def init_script(self) -> str:
        return (
            self.param("YOCTO_INIT_SCRIPT", "")
            or self.yocto_string("init_script")
            or "poky/oe-init-build-env"
        )

    def build_dir(self) -> str:
        return (
            self.param("YOCTO_BUILD_DIR", "")
            or self.yocto_string("build_dir")
            or "build-xen-qemu-421"
        )

    def bitbake_args(self) -> str:
        value = self.param("YOCTO_BITBAKE_ARGS", "") or self.yocto_string("bitbake_args")
        if not value.strip():
            self.fail("YOCTO_BITBAKE_ARGS must not be empty")
            raise AssertionError("unreachable")
        return quote_words(value)

    def graph_copy(self, default_label: str = "bitbake-graph") -> GraphCopy | None:
        output_dir = self.param("YOCTO_GRAPH_OUTPUT_DIR", "") or self.yocto_string("graph_output_dir")
        if not output_dir:
            return None
        label = self.param("YOCTO_GRAPH_LABEL", "") or self.yocto_string("graph_label") or default_label
        files = (
            self.param(
                "YOCTO_GRAPH_FILES",
                "",
            )
            or self.yocto_string("graph_files")
            or "task-depends.dot pn-buildlist recipe-depends.dot package-depends.dot"
        )
        return GraphCopy(
            output_dir=str(self.path_from_text(output_dir)),
            label=label,
            files=tuple(shlex.split(files)) or DEFAULT_GRAPH_FILES,
        )

    def invocation(self) -> YoctoInvocation:
        return YoctoInvocation(self.yocto_dir(), self.build_dir(), self.init_script())

    def command(self, bitbake_args: str, graph_copy: GraphCopy | None = None) -> str:
        return bitbake_shell_command(self.invocation(), bitbake_args, graph_copy=graph_copy)

    def run_bitbake(self, bitbake_args: str, graph_copy: GraphCopy | None = None) -> None:
        self.docker_subprocess_must_succeed(
            self.container_alias(),
            self.command(bitbake_args, graph_copy),
            timeout=int(self.param("YOCTO_BITBAKE_TIMEOUT_SEC", "0") or "0"),
            substitute_params=False,
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
            avoid_printing_command=self.bool_param("YOCTO_BITBAKE_HIDE_COMMAND"),
            avoid_printing_command_reason=self.param(
                "YOCTO_BITBAKE_HIDE_COMMAND_REASON",
                "The command contains sensitive information",
            ),
            avoid_printing_command_output=self.bool_param("YOCTO_BITBAKE_HIDE_OUTPUT"),
            avoid_printing_command_output_reason=self.param(
                "YOCTO_BITBAKE_HIDE_OUTPUT_REASON",
                "The command output contains sensitive information",
            ),
        )


class bitbake(YoctoTask):
    """Run `bitbake <YOCTO_BITBAKE_ARGS>`."""

    def __init__(self):
        super().__init__()
        self.set_name(bitbake.__name__)

    def execute(self):
        self.run_bitbake(self.bitbake_args(), self.graph_copy())


class bitbake_target(YoctoTask):
    """Run `bitbake <YOCTO_TARGET>`."""

    def __init__(self):
        super().__init__()
        self.set_name(bitbake_target.__name__)

    def execute(self):
        target = self.param("YOCTO_TARGET", "") or ""
        if not target.strip():
            self.fail("YOCTO_TARGET must not be empty")
            raise AssertionError("unreachable")
        self.run_bitbake(quote_words(target))


class bitbake_clean_target(YoctoTask):
    """Run `bitbake -c <YOCTO_CLEAN_TASK> <YOCTO_TARGET>`."""

    def __init__(self):
        super().__init__()
        self.set_name(bitbake_clean_target.__name__)

    def execute(self):
        target = self.param("YOCTO_TARGET", "") or ""
        clean_task = self.param("YOCTO_CLEAN_TASK", "clean") or "clean"
        if not target.strip():
            self.fail("YOCTO_TARGET must not be empty")
            raise AssertionError("unreachable")
        if clean_task not in ("clean", "cleansstate", "cleanall"):
            self.fail("YOCTO_CLEAN_TASK must be one of: clean, cleansstate, cleanall")
            raise AssertionError("unreachable")
        self.run_bitbake(f"-c {shlex.quote(clean_task)} {quote_words(target)}")


class bitbake_graph_target(YoctoTask):
    """Run `bitbake -g <YOCTO_TARGET>` and copy generated graph files."""

    def __init__(self):
        super().__init__()
        self.set_name(bitbake_graph_target.__name__)

    def execute(self):
        target = self.param("YOCTO_TARGET", "") or ""
        if not target.strip():
            self.fail("YOCTO_TARGET must not be empty")
            raise AssertionError("unreachable")
        self.run_bitbake(
            f"-g {quote_words(target)}",
            self.graph_copy(default_label="-".join(shlex.split(target))),
        )

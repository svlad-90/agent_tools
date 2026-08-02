"""PAF build and artifact tasks for the Xen/Zephyr domain."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from datetime import timezone

from paf.paf_impl import logger

from paf_workspace.domains.xen_zephyr.tasks.base import XenZephyrTask


class build_product(XenZephyrTask):
    """Build the product that provides Xen/Zephyr runtime artifacts."""

    def __init__(self):
        super().__init__()
        self.set_name(build_product.__name__)

    def execute(self):
        if self.bool_param("SKIP_PRODUCT_BUILD"):
            logger.info("Skip product build: SKIP_PRODUCT_BUILD is enabled")
            return
        split_steps = (
            (
                "PRODUCT_BUILD_YOCTO",
                self.param("PRODUCT_BUILD_YOCTO_CMD", "") or "",
                self.param("PRODUCT_BUILD_YOCTO_CONTAINER_ALIAS", "") or "",
            ),
            (
                "PRODUCT_BUILD_ZEPHYR",
                self.param("PRODUCT_BUILD_ZEPHYR_CMD", "") or "",
                self.param("PRODUCT_BUILD_ZEPHYR_CONTAINER_ALIAS", "") or "",
            ),
        )
        ran_split_step = False
        for prefix, command, container_alias in split_steps:
            if not command:
                continue
            ran_split_step = True
            self.run_domain_command(
                command,
                timeout_param=f"{prefix}_CMD_TIMEOUT_SEC",
                hide_prefix=f"{prefix}_CMD",
                container_alias=container_alias,
            )
        if ran_split_step:
            return

        command = self.param("PRODUCT_BUILD_CMD")
        if not command:
            logger.info("Skip product build: PRODUCT_BUILD_CMD is empty")
            return
        self.run_domain_command(
            command,
            timeout_param="PRODUCT_BUILD_CMD_TIMEOUT_SEC",
            hide_prefix="PRODUCT_BUILD_CMD",
            container_alias=self.param("PRODUCT_BUILD_CONTAINER_ALIAS", "") or "",
        )


class write_artifact_manifest(XenZephyrTask):
    """Write a manifest for product artifacts consumed by the runtime harness."""

    def __init__(self):
        super().__init__()
        self.set_name(write_artifact_manifest.__name__)

    def execute(self):
        manifest_path = self.path_param("ARTIFACT_MANIFEST")
        artifact_names = self.param("ARTIFACTS", "") or ""
        artifacts = []
        root = self.workspace_root()

        for name in artifact_names.split():
            path = self.path_param(f"ARTIFACT_{name}")
            self.assertion(path.exists(), f"Artifact {name} does not exist: {path}")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            try:
                stored_path = str(path.relative_to(root))
            except ValueError:
                stored_path = str(path)
            artifacts.append(
                {
                    "name": name,
                    "path": stored_path,
                    "sha256": digest,
                    "producer": self.param(
                        f"ARTIFACT_{name}_PRODUCER",
                        self.param("PRODUCT_NAME", "unknown"),
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps({"artifacts": artifacts}, indent=2) + "\n")
        logger.info(f"Wrote artifact manifest: {manifest_path}")

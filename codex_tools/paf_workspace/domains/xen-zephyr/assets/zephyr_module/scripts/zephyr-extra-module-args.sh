#!/usr/bin/env bash
set -euo pipefail

module_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
printf -- '# Use this for builds that do not discover modules through west.\n'
printf -- '-DZEPHYR_MODULES=%s\n' "${module_dir}"
printf -- '# Use this only when west already discovers the normal module set.\n'
printf -- 'export EXTRA_ZEPHYR_MODULES=%s\n' "${module_dir}"
printf -- '-DEXTRA_ZEPHYR_MODULES=%s\n' "${module_dir}"
printf -- '-DOVERLAY_CONFIG=%s/configs/dom0-console-collector.conf\n' "${module_dir}"

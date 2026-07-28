# SPDX-License-Identifier: Apache-2.0

zephyr_library()
zephyr_library_sources_ifdef(
  CONFIG_XEN_HARNESS_DOMU_CONSOLE_COLLECTOR
  log_collector.c
)

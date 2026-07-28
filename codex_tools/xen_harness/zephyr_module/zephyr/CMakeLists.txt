# SPDX-License-Identifier: Apache-2.0

zephyr_include_directories(include)

if(CONFIG_XEN_HARNESS_DOMU_AUTOSTART)
  if(NOT DEFINED XEN_HARNESS_DOMU_IMAGE_LOAD_ADDR)
    message(FATAL_ERROR "CONFIG_XEN_HARNESS_DOMU_AUTOSTART requires -DXEN_HARNESS_DOMU_IMAGE_LOAD_ADDR=<preloaded DomU image address>")
  endif()

  if(NOT DEFINED XEN_HARNESS_DOMU_IMAGE_SIZE)
    message(FATAL_ERROR "CONFIG_XEN_HARNESS_DOMU_AUTOSTART requires -DXEN_HARNESS_DOMU_IMAGE_SIZE=<DomU image size>")
  endif()

  zephyr_compile_definitions(
    XEN_HARNESS_DOMU_IMAGE_LOAD_ADDR=${XEN_HARNESS_DOMU_IMAGE_LOAD_ADDR}
    XEN_HARNESS_DOMU_IMAGE_SIZE=${XEN_HARNESS_DOMU_IMAGE_SIZE}
  )
endif()

add_subdirectory(lib)

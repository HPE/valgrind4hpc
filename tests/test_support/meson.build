# Meson build definition for the valgrind4hpc test support libraries.
#
# Copyright 2014-2025 Hewlett Packard Enterprise Development LP.

gtest_root = 'googletest/googletest'
gmock_root = 'googletest/googlemock'

gtest_internal_inc = include_directories(gtest_root, gtest_root / 'include')
gmock_internal_inc = include_directories(gmock_root, gmock_root / 'include')

gtest_lib = static_library('gtest',
  sources: [gtest_root / 'src/gtest-all.cc'],
  include_directories: gtest_internal_inc,
  dependencies: [thread_dep],
  build_by_default: false,
  install: false)

gtest_dep = declare_dependency(
  link_with: gtest_lib,
  include_directories: include_directories(gtest_root / 'include'),
  dependencies: [thread_dep])

gmock_lib = static_library('gmock',
  sources: [gmock_root / 'src/gmock-all.cc'],
  include_directories: [gtest_internal_inc, gmock_internal_inc],
  dependencies: [thread_dep],
  build_by_default: false,
  install: false)

gmock_dep = declare_dependency(
  link_with: gmock_lib,
  include_directories: include_directories(gmock_root / 'include'),
  dependencies: [gtest_dep])

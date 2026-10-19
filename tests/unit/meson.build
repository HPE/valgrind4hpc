# Meson build definition for the valgrind4hpc unit tests.
#
# Copyright 2014-2025 Hewlett Packard Enterprise Development LP.

googletest_subproject = cmake.subproject('googletest')
gmock_dep = googletest_subproject.dependency('gmock')
gtest_dep = googletest_subproject.dependency('gtest')
googletest_dep = declare_dependency(dependencies: [gmock_dep, gtest_dep])

unit_tests = executable('unit_tests',
  sources: [
    'unit_tests.cpp',
    'valgrind4hpc_aggregator_test.cpp',
    'MsgQueue_test.cpp',
    'TSQueue_test.cpp',
    'XmlChunker_test.cpp',
    'Socket_test.cpp',
    'ExecvpOutput_test.cpp',
  ],
  include_directories: [valgrind4hpc_inc],
  dependencies: [config_dep, googletest_dep, mrnet_dep, boost_dep,
                 thread_dep, dl_dep, rt_dep],
  cpp_args: ['-fPIC'],
  link_args: ['-Wl,--as-needed'],
  build_by_default: false,
  install: false)

test('unit_tests', unit_tests, timeout: 300)

# Meson build definition for the valgrind4hpc components.
#
# Copyright 2015-2025 Hewlett Packard Enterprise Development LP.

valgrind4hpc_inc = include_directories('.')

common_link_args = ['-Wl,--as-needed']
cti_fe_lib_dir = cti_fe_dep.get_variable(pkgconfig: 'libdir')
cti_be_lib_dir = cti_be_dep.get_variable(pkgconfig: 'libdir')

executable('valgrind4hpc',
  sources: ['valgrind4hpc_FE.C'],
  include_directories: valgrind4hpc_inc,
  dependencies: [config_dep, cti_fe_dep, mrnet_dep, boost_dep, thread_dep],
  link_args: common_link_args,
  install_rpath: install_libdir + ':' + cti_fe_lib_dir,
  install: true)

executable('valgrind4hpc_daemon',
  sources: ['valgrind4hpc_BE.C', 'ValgrindOutput.C'],
  include_directories: valgrind4hpc_inc,
  dependencies: [config_dep, cti_be_dep, mrnet_dep, boost_dep, thread_dep],
  link_args: common_link_args,
  install_rpath: install_libdir + ':' + cti_be_lib_dir,
  install: true,
  install_dir: prefix / libexecdir)

executable('valgrind4hpc_starter',
  sources: ['valgrind4hpc_starter.C'],
  include_directories: valgrind4hpc_inc,
  dependencies: [config_dep, boost_dep, thread_dep, dl_dep],
  link_args: common_link_args,
  install_rpath: install_libdir,
  install: true,
  install_dir: prefix / libexecdir)

# The front end loads this by its exact file name, so no library versioning.
shared_library('valgrind4hpc_filters',
  sources: ['valgrind4hpc_filters.C'],
  include_directories: valgrind4hpc_inc,
  dependencies: [config_dep, mrnet_dep, boost_dep],
  cpp_args: ['-fPIC'],
  link_args: common_link_args,
  install_rpath: install_libdir,
  install: true,
  install_dir: install_libdir)

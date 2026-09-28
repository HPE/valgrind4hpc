# Meson build definition for valgrind4hpc.
#
# Copyright 2015-2025 Hewlett Packard Enterprise Development LP.
#
# This is an alternative to the autotools build; the autotools files are
# still present and functional.

project('valgrind4hpc', ['c', 'cpp'],
  version: run_command('sh', '-c',
      '. "' + meson.current_source_dir() + '/release_versioning" && printf "%s.%s" "$major" "$minor"',
      check: true).stdout().strip(),
  license: 'Proprietary',
  meson_version: '>= 0.56.0',
  default_options: [
    'cpp_std=c++17',
    'warning_level=1',
    'b_ndebug=if-release',
  ])

cxx = meson.get_compiler('cpp')

################
### Options  ###
################

prefix = get_option('prefix')
libdir = get_option('libdir')
libexecdir = get_option('libexecdir')
datadir = get_option('datadir')

# Directory the installed binaries look in for the filter library and the
# helper binaries. Baked in as an rpath so the tools are relocatable.
install_libdir = prefix / libdir

####################
### Dependencies ###
####################

thread_dep = dependency('threads')
dl_dep = cxx.find_library('dl', required: false)
rt_dep = cxx.find_library('rt', required: false)

boost_dep = dependency('boost', version: '>= 1.66')

cti_fe_dep = dependency('common_tools_fe')
cti_be_dep = dependency('common_tools_be')

# Prefer a system/pkg-config cray-mrnet.pc; fall back to building it from the
# subprojects/cray-mrnet.wrap overlay (subprojects/packagefiles/cray-mrnet)
# when no cray-mrnet.pc is available in PKG_CONFIG_PATH.
mrnet_dep = dependency('cray-mrnet', method: 'pkg-config', required: false)
if mrnet_dep.found()
  # has_header()'s dependencies: kwarg only accepts external dependencies, so
  # this check is skipped for the subproject fallback below (its internal
  # dependency's header isn't even built yet at configure time).
  if not cxx.has_header('mrnet/MRNet.h', dependencies: mrnet_dep)
    error('mrnet/MRNet.h not found.')
  endif
else
  message('cray-mrnet.pc not found in PKG_CONFIG_PATH; building mrnet as a subproject.')
  mrnet_dep = dependency('cray-mrnet', fallback: ['mrnet', 'mrnet_dep'])
endif

################
### config.h ###
################

cdata = configuration_data()

cdata.set_quoted('PACKAGE', meson.project_name())
cdata.set_quoted('PACKAGE_NAME', meson.project_name())
cdata.set_quoted('PACKAGE_TARNAME', meson.project_name())
cdata.set_quoted('PACKAGE_VERSION', meson.project_version())
cdata.set_quoted('PACKAGE_STRING', meson.project_name() + ' ' + meson.project_version())
cdata.set_quoted('VERSION', meson.project_version())

check_headers = [
  'arpa/inet.h',
  'fcntl.h',
  'netdb.h',
  'netinet/in.h',
  'stdlib.h',
  'string.h',
  'sys/socket.h',
  'sys/time.h',
  'unistd.h',
]

foreach h : check_headers
  if cxx.has_header(h)
    cdata.set('HAVE_' + h.underscorify().to_upper(), 1)
  endif
endforeach

check_functions = [
  'clock_gettime',
  'dup2',
  'fork',
  'gettimeofday',
  'inet_ntoa',
  'memset',
  'select',
  'setenv',
  'socket',
  'strchr',
  'strdup',
  'strerror',
]

foreach f : check_functions
  if cxx.has_function(f)
    cdata.set('HAVE_' + f.to_upper(), 1)
  endif
endforeach

cdata.set('HAVE_MRNET', 1)

config_h = configure_file(output: 'config.h', configuration: cdata)

config_dep = declare_dependency(
  sources: config_h,
  include_directories: include_directories('.'))

###################
### Subprojects ###
###################

subdir('src')
subdir('doc/man')
subdir('suppressions')
subdir('tests')

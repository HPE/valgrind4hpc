# Meson overlay for the upstream cray-mrnet sources (see
# subprojects/cray-mrnet.wrap). cray-mrnet only ships an autotools build, so
# this drives that ./configure && make && make install flow with meson's own
# tooling (run_command/environment/custom_target) and exposes the result as
# a meson dependency named 'cray-mrnet'.
#
project('mrnet', 'c', 'cpp')

cti_fe_dep = dependency('common_tools_fe')
pkgconfig = find_program('pkg-config')

# includedir/libdir are standard pkg-config variables, so read them straight
# off the dependency instead of re-invoking pkg-config.
cti_include_dir = cti_fe_dep.get_variable(pkgconfig: 'includedir')
cti_lib_dir = cti_fe_dep.get_variable(pkgconfig: 'libdir')

# Dependency objects don't expose their assembled Cflags/Libs as strings
# (only named pkg-config variables via get_variable()), so the full flags
# needed for the configure/make env still have to come from pkg-config
# itself.
mrnet_cflags = run_command(pkgconfig, ['--cflags', 'common_tools_fe'], check: true).stdout().strip()
mrnet_libs = run_command(pkgconfig, ['--libs', 'common_tools_fe'], check: true).stdout().strip()

mrnet_lib_dirs = run_command(pkgconfig, ['--libs-only-L', 'common_tools_fe'], check: true).stdout().strip().split()
mrnet_rpaths = []
foreach lib_dir_arg : mrnet_lib_dirs
  if lib_dir_arg.startswith('-L')
    mrnet_rpaths += '-Wl,-rpath,' + lib_dir_arg.substring(2)
  endif
endforeach

mrnet_ldflags = ' '.join([mrnet_libs] + mrnet_rpaths + ['-Wl,-rpath,\'$$ORIGIN\''])

mrnet_env = environment()
mrnet_env.set('CFLAGS', mrnet_cflags)
mrnet_env.set('CXXFLAGS', mrnet_cflags)
mrnet_env.set('LDFLAGS', mrnet_ldflags)
mrnet_env.set('SOFLAGS', mrnet_libs)

install_dir = meson.current_build_dir() / 'install'
mrnet_include_dir = install_dir / 'include'
mrnet_lib_dir = install_dir / 'lib'

sh = find_program('sh')
make = find_program('make')

# Out-of-tree autotools build: configure/make/install all run with cwd set
# to this target's build dir, pointed at the checked-out source directory.
mrnet_configure = custom_target('mrnet-configure',
  output: 'config.status',
  command: [
    meson.current_source_dir() / 'configure',
    '--prefix=' + install_dir,
    '--with-startup=cray-cti',
    '--enable-shared',
    '--with-craycti-inc=' + cti_include_dir,
    '--with-craycti-lib=' + cti_lib_dir,
  ],
  env: mrnet_env,
  console: true,
)

# parallel builds are broken with mrnet, so no -j here
mrnet_build = custom_target('mrnet-make',
  output: 'mrnet-build.stamp',
  depends: mrnet_configure,
  command: [sh, '-c', make.full_path() + ' && touch @OUTPUT@'],
  env: mrnet_env,
  console: true,
)

mrnet_install = custom_target('mrnet-install',
  output: 'mrnet-install.stamp',
  depends: mrnet_build,
  command: [sh, '-c', make.full_path() + ' install && touch @OUTPUT@'],
  env: mrnet_env,
  console: true,
  build_by_default: true,
)

mrnet_config_headers = custom_target('mrnet-config-headers',
  output: 'mrnet-config-headers.stamp',
  depends: mrnet_install,
  command: [
    sh,
    '-c',
    'set -e; build_subdir=$(find build -mindepth 1 -maxdepth 1 -type d | head -n1); cp -a "$build_subdir/xplat_config.h" "$1/include/."; cp -a "$build_subdir/mrnet_config.h" "$1/include/."; touch "$2"',
    'copy-mrnet-config-headers',
    install_dir,
    '@OUTPUT@',
  ],
  console: true,
  build_by_default: true,
)

meson.add_install_script(
  sh,
  '-c',
  'set -e; dest="$MESON_INSTALL_DESTDIR_PREFIX/$1"; mkdir -p "$dest"; cp -a "$2"/libmrnet.so* "$2"/libxplat.so* "$dest"/',
  'install-mrnet-libraries',
  get_option('libdir'),
  mrnet_lib_dir,
)

mrnet_dep = declare_dependency(
  sources: mrnet_config_headers,
  compile_args: ['-I' + mrnet_include_dir],
  link_args: ['-L' + mrnet_lib_dir, '-lmrnet', '-lxplat'],
  dependencies: [cti_fe_dep],
)


meson.override_dependency('mrnet', mrnet_dep)

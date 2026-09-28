# Meson build definition for the valgrind4hpc suppression files.
#
# Copyright 2017-2025 Hewlett Packard Enterprise Development LP.

# The front end expects to find these under <prefix>/share/suppressions
supp_install_dir = datadir / 'suppressions'

supp_generator = executable('supp_generator',
  sources: ['suppression_generator.C'],
  install: false)

foreach supp : ['libmpich_cray', 'libpmi', 'misc']
  custom_target(supp + '.supp',
    input: 'in_files' / (supp + '.in'),
    output: supp + '.supp',
    command: [supp_generator, '-f', '@INPUT@', '-o', '@OUTPUT@'],
    build_by_default: true,
    install: true,
    install_dir: supp_install_dir)
endforeach

install_data(
  ['libfabric.supp', 'fixed_supp/known.supp', 'fixed_supp/libcxi.supp'],
  install_dir: supp_install_dir)

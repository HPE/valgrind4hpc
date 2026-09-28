# Meson build definition for the valgrind4hpc man page.
#
# Copyright 2015-2025 Hewlett Packard Enterprise Development LP.

install_man('valgrind4hpc.1')

# Optional convenience target to regenerate the man page from markdown.
pandoc = find_program('pandoc', required: false)
if pandoc.found()
  run_target('man',
    command: [pandoc, '-s', '-t', 'man',
      meson.current_source_dir() / 'valgrind4hpc.1.md',
      '-o', meson.current_source_dir() / 'valgrind4hpc.1'])
endif

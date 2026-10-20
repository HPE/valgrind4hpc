# CPEDocs

This directory contains material for automating the deployment of valgrind4hpc
documentation in the CPEDocs project.

https://github.hpe.com/hpcde/doc-cpe

## Usage Instructions

### Instructions for CPEDocs Maintainers

1. Set your current working directory to the directory that contains this README.
2. Run `./collect_cpedocs.sh`. This will create a new directory called
   `cpedocs_valgrind4hpc/`.
3. Copy `cpedocs_valgrind4hpc/` and its contents into `/CPEDocs/doc/debugging-tools/`,
   where `/CPEDocs/` is the root of the CPEDocs repository.

### Instructions for valgrind4hpc Maintainers

In general, just ensure that `./collect_cpedocs.sh` doesn't break and its generated
content doesn't become outdated.

#### Maintaining `cpedocs_index_chunk.md`

`cpedocs_index_chunk.md` is included in-place in the CPEDocs debugging tools top level
index file.

Since it is part of a larger file, the highest level header level should be 2 (##). Assume
that valgrind4hpc content will live in a directory called `./cpedocs_valgrind4hpc` for
links. The `cpedocs_valgrind4hpc` directory is created by the `collect_cpedocs.sh` script.

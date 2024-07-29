# CPEDocs

This directory contains material for automating the deployment of valgrind4hpc
documentation in the CPEDocs project.

https://github.hpe.com/hpcde/doc-cpe

## Maintenance

In general, just ensure that `./collect_cpedocs.sh` doesn't break and its generated
content doesn't become outdated.

### Maintaining `index.md`

`index.md` is included in-place in the CPEDocs debugging tools top level index file.

Since it is part of a larger file, the highest level header level should be 2 (##). Assume
that valgrind4hpc content will live in a directory called `./valgrind4hpc` for
links. The `valgrind4hpc` directory is created by the `collect_cpedocs.sh` script.

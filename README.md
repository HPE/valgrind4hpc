# valgrind4hpc

## Usage

Valgrind4hpc is a Valgrind-based debugging tool to aid in the detection of memory
leaks and errors in parallel applications. Valgrind4hpc aggregates any duplicate
messages across ranks to help provide an understandable picture of program behavior.

- [User Guide](./doc/guides/user_guide.md)
- [valgrind4hpc man page](./doc/man/valgrind4hpc.1.md)

## Building

### Requirements

HPE packages

- cray-devel, either built locally or via a cray-cti-devel rpm.

Packages needed to build.

- meson
- boost
- xz-devel
- zlib-devel

Runtime dependencies

- valgrind.   The CPE rpms bundled an internal build of valgrind.
- cti
- cray-mrnet if used in a CPE environment.

### Dual build modes

This version of atp supports building either stand-alone or within
the HPE build pipelines.  This is mosly confinded to the 'hpe'
directory, but there are some ".sh" and ".yaml" files that are
required to live in the top level directory.  Also, the HPE build
relies on submodules.  For the open source build, _you do not need to
`git submodule update`_ which would fail because they refer to
internal repositories.

### Building HPE tools in a shared directory

Given a shared prefix `$prefix`, you can build cti and valgrind4hpc in turn with:

```bash
export PKG_CONFIG_PATH=$prefix/lib/cti/pkgconfig:$PKG_CONFIG_PATH

for i in cti valgrind4hpc; do
   pushd $i
   meson setup -Dprefix=$prefix -Dlibdir=lib/$i -Dlibexecdir=libexec/$i ./build
   popd
done
```

Assuming you've installed the prequisites for both packages.

One could potentially create a cti.wrap file to build
the dependencies as meson subprojects, but the build definitions are
not expected to be stable enough yet for that approach to be reliable.

### GitHub Actions

Building is currently only set up within the HPE environment which is
automated via GitHub Actions in .github/workflows/build_pipeline.yaml

### Setting up a development system in an HPE environment.

The build scripts can be used directly assuming you have access to the
internal HPE artifactory and GitHub repo to get the dependencies.

#### Initial set-up

After checking out a version of the repository:

- `git submodule update --init --recursive`
- manually update the `build_number` variable in the
     "release_versioning" file

#### Installing dependencies

The valgrind4hpc build is set up to work on a VM based on one of the supported
OS's and that you have root access to add dependencies

- `sudo ./hpe/runBuildPrep.sh`

This installs the packages needed for the build.    This is rpms from
the OS, like compilers and "devel" packages, plus the CDST rpms from
the artifactory:

- cray-cti
- cray-mrnet
- cray-dyninst

### Building ATP

The build is set up to build the artifacts into the expected CPE
install location: /opt/cray/pe/atp/[version]

You can either make sure the directory "/opt/cray/pe" is writable by
you, or continue the build as root.

To build:

`./hpe/runBuild.sh` builds the ATP binaries.

The actual build is set up via autotools, so inside the script it's
just doing the `./configure; make; make install` cycle.   So during a
development cycle, you can often just use `make` or `make install`
unless you've added a source file or changed build flags.

### Building the rpms

`./hpe/runBuildPackage.sh` creates the valgrind4hpc and valgrind4hpc-test rpms.


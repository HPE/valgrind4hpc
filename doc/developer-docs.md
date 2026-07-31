# valgrind4hpc Developer Guide

## 1. Product Overview

valgrind4hpc launches every rank of a high-performance computing (HPC) application under Valgrind, collects the rank-local Valgrind XML streams, and merges equivalent findings into one report. Merged blocks track ranks, so a developer can distinguish a rank-specific leak from an error shared by the whole job without reading one Valgrind report per process. The user-facing behavior is described in `doc/guides/user_guide.md` and `doc/man/valgrind4hpc.1.md`.

### Runtime design

The runtime separates launch control, per-rank process setup, local parsing, network reduction, and final presentation:

1. **Frontend - `src/valgrind4hpc_FE.C`**
   - Parses the valgrind4hpc command line.
   - Uses the Common Tools Interface (CTI) to launch and inspect the target application.
   - Detects whether the target uses a supported parallel runtime.
   - Builds the MRNet reduction topology.
   - Receives reduced error, leak, summary, suppression, and count streams.
   - Performs the final rank-set merge and writes the report to standard output or `--outputfile`.
2. **Per-rank starter - `src/valgrind4hpc_starter.C`**
   - Receives the Valgrind path, temporary directory, and socket information from the backend daemon.
   - Constructs the per-rank Valgrind invocation.
   - Sets runtime variables such as `VALGRIND_LIB`, `TMPDIR`, and the optional DMAPP preload.
   - Starts the instrumented application rank.
3. **Backend daemon - `src/valgrind4hpc_BE.C`**
   - Uses CTI to map operating-system process IDs to application ranks.
   - Passes startup data to each starter through a System V message queue.
   - Accepts rank-local socket connections.
   - Splits and parses Valgrind XML with `src/utils/XmlChunker.hpp` and `src/ValgrindOutput.*`.
   - Emits typed MRNet messages for errors, leaks, summaries, suppressions, counts, and shutdown.
4. **MRNet filters - `src/valgrind4hpc_filters.C`**
   - Reduce equivalent messages before they reach the frontend.
   - Preserve the rank bitset associated with each distinct message.
5. **Final aggregation - `src/valgrind4hpc_aggregator.h`**
   - Merges duplicate text blocks and their rank sets.
   - Formats compact `RANKS:` ranges for the user-facing report.

The message tags shared by these components live in `src/valgrind4hpc_protocol.h`. Runtime constants and environment-variable names live in `src/valgrind4hpc_defs.h`.

### External systems and libraries

- **Valgrind** runs the application rank and produces the XML consumed by the backend. The repository carries an HPE Valgrind mirror as `external/valgrind`.
- **CTI** controls the workload-manager launch and exposes rank, process, node, and staging information to the frontend and backend.
- **MRNet** distributes backend daemons and reduces messages through a tree before delivery to the frontend.
- **Boost** supplies dynamic bitsets, property-tree XML parsing, and string utilities. `configure.ac` requires Boost 1.69 or newer.
- **The workload manager (WLM)** launches the application. Source and test configuration account for Slurm, ALPS, PALS, and SSH-backed test launches.
- **Cray PE modules** provide CTI, MRNet, Dyninst, compilers, and optional SHMEM support.

### Repository layout

- **`src/` - product implementation**
  - `valgrind4hpc_FE.C` - frontend command, CTI launch, MRNet topology, and final aggregation.
  - `valgrind4hpc_BE.C` - backend daemon, rank mapping, XML ingestion, and typed message production.
  - `valgrind4hpc_starter.C` - per-rank Valgrind process setup.
  - `valgrind4hpc_filters.C` - MRNet reduction filters.
  - `ValgrindOutput.*` - parser state and normalized Valgrind blocks.
  - `utils/` - socket, message queue, process, file-descriptor, and XML helpers.
- **`tests/` - test layers**
  - `unit/` - GoogleTest-based C++ unit tests.
  - `test_support/` - vendored GoogleTest and GoogleMock build targets.
  - `function/` - Avocado-based MPI and SHMEM product tests and output fixtures.
  - `coverage/` - gcovr and Sonar coverage recipes.
- **`suppressions/` - built-in Valgrind suppression generation and fixed suppressions.**
- **`doc/` - user guide, man page source, and CPEDocs collection.**
- **`rpmbuild/` - RPM specification, templates, release-note inputs, and package outputs.**
- **`external/` - build-library, Valgrind, and changelog submodules.**
- **Root build files**
  - `configure.ac` and `Makefile.am` - Autotools configuration.
  - `build.sh` and `container_def.yaml` - `dst-rpm` container orchestration.
  - `runBuildPrep.sh`, `runBuild.sh`, `runBuildPackage.sh`, and `runInstallTest.sh` - lower-level pipeline stages.
  - `release_versioning` - product and libtool version policy.

### Terminology

- **FE / frontend:** the user-facing `valgrind4hpc` process.
- **BE / backend:** a `valgrind4hpc_daemon` process placed on a compute node.
- **Starter:** the per-rank `valgrind4hpc_starter` wrapper that execs Valgrind and the target.
- **CTI:** Common Tools Interface, used for workload-manager control and rank/process discovery.
- **MRNet:** the tree-based communication and reduction layer between backends and the frontend.
- **Suppression:** a Valgrind rule that removes a known or irrelevant diagnostic from the report.
- **WLM:** workload manager, such as Slurm, ALPS, or PALS.

## 2. Environment Setup

### Access prerequisites

Ensure you have access to the following resources:

- Read access to the private HPE GitHub repositories named in `.gitmodules`.
- Read access to the Artifactory index and container registries referenced by `build.sh` and `container_def.yaml`.
- Access to the Cray PE package/module repositories that provide CTI, MRNet, Dyninst, compilers, and `set_default`.
- For CI work, access to the self-hosted GitHub Actions environment and the reusable `hpcde/devops-shared-workflows` workflow.
- For functional testing, access to an HPC system with a supported WLM and permission to launch MPI jobs. Interactive VGDB debugging also requires direct SSH access to compute nodes.

Provisioning details are intentionally not duplicated here; they are organizational controls rather than product design.

### Initialize repository dependencies

Initialize every submodule because the product build, unit tests, functional harness, packaging, and release-note generation use different submodules:

```bash
git submodule update --init --recursive
```

The important submodules are:

- `external/cdst_build_library` - lower-level build helpers.
- `external/valgrind` - HPE Valgrind source mirror.
- `external/changelog` - release-note tooling.
- `rpmbuild/SOURCES/set_default` - module default-management tooling.
- `tests/test_support/googletest` - unit-test framework source.
- `tests/function/cdst-test` - functional-test orchestration.

### Supported build targets

`container_def.yaml` defines the package build matrix:

- RHEL 8.10 on x86-64.
- RHEL 9.5 and 9.6 on x86-64 and AArch64.
- SLES 15 SP6 and SP7 on x86-64 and AArch64.

Each target uses an internal build image and enters through `rpmBuild.sh`. Do not treat an arbitrary developer workstation as equivalent to these target images.

### Toolchain and package prerequisites

The container preparation stage in `runBuildPrep.sh` installs the operating-system toolchain. Its RHEL and SLES package lists include:

- Autoconf, Automake, autoconf-archive, libtool, M4, and Make.
- GCC/binutils development tools, Bison, Flex, and ctags.
- ncurses, bzip2, xz, and zlib development packages.
- RPM build tooling.
- DocBook/XSL and Texinfo tooling used by bundled components.
- Python 3 and pip.

The direct product configuration additionally requires:

- Boost 1.69 or newer.
- `common_tools_fe` and `common_tools_be` through `pkg-config`.
- the MRNet library, headers, and `cray-mrnet` package metadata.
- a C++ compiler accepted by Autoconf; product targets explicitly compile as C++11

The lower-level build script loads these modules before configuration:

```bash
module load cray-cti-devel
module load cray-dyninst
module load cray-mrnet
```

### Build and runtime environment variables

- **Container/build orchestration**
  - `PRODUCT` - product stream passed to `dst-rpm`; `build.sh` supplies `pe-base` when unset.
  - `BUILD_TARGETS` - comma-separated names from `container_def.yaml`.
  - `LOCAL_BUILD` - nonempty for a local `dst-rpm` build; cleared by `build.sh -n`.
  - `BUILD_METADATA` - package version metadata consumed by the RPM spec.
  - `BUILD_NUMBER`, `BRANCH_NAME` - CI inputs used to form package versions and select release behavior.
- **Runtime location**
  - `VALGRIND4HPC_INSTALL_DIR` - required base directory for the frontend's installed helpers, libraries, and suppressions.
  - `VALGRIND4HPC_VALGRIND_DIR` - optional alternate Valgrind installation.
  - `VALGRIND4HPC_IGNORE_SUPPRESSIONS` - disables the default suppression set when present.
  - `MRNET_INSTALL_DIR` - MRNet installation used to extend the runtime path.
  - `VALGRIND_LIB` - Valgrind core/tool directory used by the starter.
- **Diagnostics**
  - `CTI_DEBUG` - enables timed backend logging when paired with `CTI_LOG_DIR`.
  - `CTI_LOG_DIR` - directory for per-host, component, and process log files.
- **Target application build**
  - `CRAYPE_LINK_TYPE=dynamic` - directs the Cray compiler to produce a dynamic target that Valgrind can instrument.

## 3. How to Build

There are two supported views of the build. `build.sh` is the developer-facing container orchestrator; the `runBuild*.sh` scripts expose the direct Autotools and packaging pipeline executed inside a prepared Cray PE build environment.

### Container-orchestrated build

`build.sh` creates or activates `dstlibvenv`, installs the internal `craydstlib` tooling, obtains build metadata, and delegates to `dst-rpm`. Select one or more names from `container_def.yaml`:

```bash
./build.sh -t rhel_9_6_x86_64
```

With no `-t`, `BUILD_TARGETS` remains empty and target selection is left to `dst-rpm`. `-n` or `--not-local` selects the non-local path, which adds signing and Artifactory metadata upload behavior:

```bash
./build.sh --not-local -t sles15_sp7_aarch64
```

The container path is structured as follows:

1. `build.sh` calls `dst-rpm build` for the selected target definition.
2. The target in `container_def.yaml` enters `rpmBuild.sh`.
3. `rpmBuild.sh` calls `runBuild.sh` to build bundled Valgrind and valgrind4hpc.
4. The repository exposes preparation, packaging, and install-check scripts around that target; the reusable workflow decides which stages to invoke.

### Direct Autotools build pipeline

Use this path inside a prepared RHEL or SLES Cray PE environment. The scripts assume the repository root as the working directory and source helpers from `external/cdst_build_library`.

1. Install operating-system and Cray PE dependencies:

   ```bash
   ./runBuildPrep.sh
   ```

2. Build bundled Valgrind and valgrind4hpc:

   ```bash
   ./runBuild.sh
   ```

   The script performs these product steps after module setup:

   ```bash
   autoreconf -ifv
   ./configure --prefix="$install_dir" --with-boost="$CRAY_DYNINST_INSTALL_DIR"
   make $cdst_j_flags
   make $cdst_j_flags install
   ```

   Pass `--nodeps` to skip only the bundled Valgrind build. Supply a compatible Valgrind payload before packaging:

   ```bash
   ./runBuild.sh --nodeps
   ```

3. Generate CPEDocs content, release notes, and RPMs:

   ```bash
   ./runBuildPackage.sh
   ```

   The package stage ends with the repository-defined RPM command:

   ```bash
   rpmbuild -bb -D "_topdir ${PWD}/rpmbuild" rpmbuild/SPECS/valgrind4hpc.spec
   ```

### Build products and installation layout

`src/Makefile.am` defines the product binaries and library:

```make
# src/Makefile.am
bin_PROGRAMS = valgrind4hpc
libexec_PROGRAMS = valgrind4hpc_daemon valgrind4hpc_starter
lib_LTLIBRARIES = libvalgrind4hpc_filters.la
```

The direct build installs under `/opt/cray/pe/valgrind4hpc/<version>/`. The RPM spec packages:

- `bin/valgrind4hpc` and the bundled Valgrind command-line tools.
- `libexec/valgrind4hpc_daemon` and `libexec/valgrind4hpc_starter`.
- `lib/libvalgrind4hpc_filters.so`.
- Valgrind headers, core files, shared objects, and `valgrind.pc`.
- `share/man/man1/` and `share/guides/`.
- `share/suppressions/`.
- Tcl and Lmod modulefiles under the Cray PE module roots.

RPM files are produced below `rpmbuild/RPMS/<architecture>/`. The non-local `dst-rpm` path also handles generated RPM metadata under `workspaces/`.

### Configuration failures

- **Boost detection fails**
  - `configure.ac` requires Boost 1.69 or newer.
  - Load the Dyninst/Boost-providing environment and pass its root through `--with-boost` as `runBuild.sh` does.
- **`libcommontools_fe.so` or `libcommontools_be.so` is not found**
  - The CTI development module or its `pkg-config` path is missing.
  - Load `cray-cti-devel` before configuration.
- **MRNet library or `mrnet/MRNet.h` is not found**
  - Load `cray-mrnet` and confirm its library, header, and package metadata paths belong to the same installation.
- **Valgrind submodule is rejected**
  - `runBuild.sh` checks for `external/valgrind/README` before building.
  - Initialize the submodules rather than bypassing the check.
- **The package manager is rejected during preparation**
  - `runBuildPrep.sh` supports only its zypper and yum branches.
  - Use one of the container targets from `container_def.yaml`.

## 4. How to Test

The test design has four layers. Commands below identify repository entry points; this guide records no execution result.

### C++ unit tests

Automake builds one GoogleTest executable, `unit_tests`, when `make check` is requested after configuration:

```make
# tests/unit/Makefile.am
TESTS = unit_tests
check_PROGRAMS = unit_tests
```

The executable covers:

- rank/message aggregation and eviction behavior;
- `MsgQueue` and `TSQueue` operations;
- XML chunk boundaries;
- socket acceptance;
- child-process output capture through `ExecvpOutput`.

GoogleTest and GoogleMock are built from `tests/test_support/googletest` as check-only libraries. The source-defined unit entry point is:

```bash
make check
```

Run it only after the same Autotools configuration used for the product, because the generated test Makefiles inherit CTI and MRNet settings.

### Functional tests

`tests/function/` contains Avocado tests driven by the `cdst-test` submodule. The harness:

1. Checks that the environment can compile and launch MPI jobs.
2. Creates a local Avocado environment according to `test_tool_config.yaml`.
3. Builds C fixtures from `tests/function/src/` with `cc -g -O0`.
4. Loads the `valgrind4hpc` module.
5. Launches the installed tool with two ranks.
6. Captures each case in `tests/function/tmp/<test-name>.out`.
7. Compares normalized output with patterns in `tests/function/tests.py.data/`.

The repository entry point is:

```bash
cd tests/function
./test_tool.py
```

Useful source-defined selectors are:

```bash
# Run a named Avocado test class or method accepted by the harness.
./test_tool.py --test <test>

# Reuse already-built fixture binaries.
./test_tool.py --skip-build

# Remove harness-created local files.
./test_tool.py --clean
```

The functional cases cover nonexistent targets, target exit codes, clean reports, leaks, illegal frees, out-of-bounds reads and writes, MPI allocation functions, rank filtering, and available SHMEM paths. `tests/function/test_tool_config.yaml` controls modules, WLM arguments, host overrides, and parallel-job counts. Do not encode machine-specific values in `tests.py`; keep them in this YAML layer.

### Package installation check

`runInstallTest.sh` is a package lifecycle check rather than a source-level test. It:

- finds RPMs under `rpmbuild/RPMS/<architecture>/`;
- installs them with yum or zypper;
- requires the installed `release_notes.md`;
- under CI branch context, removes the package and checks that its versioned install directory is gone.

It requires a built RPM set, supported package manager, and sufficient privilege:

```bash
./runInstallTest.sh
```

### Coverage structure

`configure.ac` wires `AX_CODE_COVERAGE` into compilation. `tests/coverage/Makefile` defines gcovr XML generation and a Sonar upload target. Its prerequisite recipe references `tests/function/run_tests.py` and `tests/cc_valgrind4hpc_shmem.ar`, neither of which is part of the checked-in repository layout. Treat that recipe as maintenance work, not as the canonical test entry point, until those references are reconciled.

### CI structure

`.github/workflows/build_pipeline.yaml` runs on:

- pushes to `master` and `release/**`;
- pull requests;
- manual dispatch with a target selector.

It delegates each RHEL/SLES and x86-64/AArch64 job to `hpcde/devops-shared-workflows/.github/workflows/full_workflow.yaml@main` and inherits repository secrets. The local workflow defines the platform matrix, not the internal test commands or artifact-retention policy; consult the referenced reusable workflow when changing CI stage behavior.

## 5. How to Maintain

### Version and ABI policy

`release_versioning` is the source for the product release components and libtool policy. `configure.ac` consumes the product major and minor values; packaging helpers consume the full release shape and CI build number.

Apply the documented libtool rules:

- For an implementation-only change that preserves the API, increment `revision`.
- For an added backward-compatible interface, increment `current` and `age`, and reset `revision` to zero.
- For a removed or changed interface, increment `current`, and reset `revision` and `age` to zero.
- When the product major changes, reset minor and revision. When minor changes, reset revision.

After a version-file change, regenerate Autotools outputs with the commands named in `release_versioning`:

```bash
autoreconf -ifv
./configure
```

### Dependency updates

Dependencies fall into two groups:

- **Private submodules** are pinned by the parent repository. Update the relevant submodule commit and review the consuming build or test path in the same change.
- **Cray PE package dependencies** are expressed by the RPM spec. `rpmbuild/SOURCES/get_package_data` derives compatible CTI and MRNet ranges from source-controlled version data.

A Valgrind update affects more than `external/valgrind`: review packaged binaries and core files in `rpmbuild/SPECS/valgrind4hpc.spec`, parser assumptions in `src/ValgrindOutput.*`, and built-in suppressions.

### RPM packaging

`runBuildPackage.sh` performs three product-specific operations before invoking `rpmbuild`:

1. Runs `doc/cpedocs/collect_cpedocs.sh` as a documentation-collection check.
2. Generates release-note inputs through `external/changelog`.
3. Builds `rpmbuild/SPECS/valgrind4hpc.spec`.

The spec assembles the versioned `/opt/cray/pe/valgrind4hpc` tree, modulefiles, dependency resolver, default-version helper, runtime libraries, Valgrind payload, documentation, suppressions, and functional-test RPM. Its post-install and uninstall sections also maintain module paths, the dynamic-library cache list, and version defaults.

### Documentation

- Edit the command reference in `doc/man/valgrind4hpc.1.md`; `doc/man/valgrind4hpc.1` is the generated man page delivered by the build.
- Edit end-user workflows in `doc/guides/user_guide.md`.
- Keep `doc/cpedocs/index.md` links relative to the collected `valgrind4hpc/` directory.
- Run the collector from its own directory when changing CPEDocs inputs:

  ```bash
  cd doc/cpedocs
  ./collect_cpedocs.sh
  ```

The collector copies the index, Markdown man page, and guides into a CPEDocs-compatible directory and rewrites the man-page heading for search presentation.

### Built-in suppressions

`suppressions/Makefile.am` generates suppression files from `suppressions/in_files/` and installs them with fixed suppressions. `suppressions/suppression_generator.C` expects one function per input line and emits Valgrind Memcheck and parameter suppression forms.

- Add generated-rule inputs under `suppressions/in_files/`.
- Add rules that cannot be generated under `suppressions/fixed_supp/`.
- Keep `suppressions/old_supp/` as reference only; its README explicitly excludes it from generation.
- Update the installed-file list in the RPM spec when adding a new delivered suppression file.

## 6. How to Triage

### Start with the failure boundary

- **Configuration failure:** inspect `config.log`, the loaded module set, and the CTI/MRNet/Boost package metadata used by `configure.ac`.
- **Launch failure before rank output:** inspect frontend diagnostics from `src/valgrind4hpc_FE.C`, CTI staging, WLM arguments, and MRNet location.
- **Backend or aggregation failure:** enable CTI logs and inspect backend XML, socket, queue, and MRNet errors.
- **Unexpected report content:** compare parser behavior in `src/ValgrindOutput.*`, rank merging in `src/valgrind4hpc_aggregator.h`, MRNet filters, and active suppression files.
- **Functional-test mismatch:** inspect the captured file in `tests/function/tmp/`, the corresponding pattern in `tests/function/tests.py.data/`, and the fixture source in `tests/function/src/`.

### Enable backend logs

Set both variables before launching valgrind4hpc:

```bash
export CTI_DEBUG=1
export CTI_LOG_DIR=/path/to/writable/log-directory
```

`src/timed_logging.hpp` writes one file per host, component, and process:

```text
<CTI_LOG_DIR>/<hostname>.<component>.<pid>.log
```

Each line begins with milliseconds relative to that process's first log call. Backend logging flushes each write, which makes these files useful when a daemon exits or a launch stalls.

### Target executable is rejected

- **No debug symbols:** the frontend uses `objdump` to detect supported parallel initialization symbols. Rebuild the target with `-g`, or supply `--cray-pmi=yes` or `--cray-pmi=no` when automatic detection is not possible.
- **Static target:** set `CRAYPE_LINK_TYPE=dynamic` before compiling with the Cray compiler. Valgrind requires a dynamically linked target for this workflow.
- **Target not found:** the frontend resolves the target through its explicit path or `PATH`; confirm the executable exists and is runnable in the launch environment.

### Valgrind or MRNet location is wrong

- `VALGRIND4HPC_INSTALL_DIR` must identify the versioned valgrind4hpc root.
- If bundled Valgrind is not used, set `VALGRIND4HPC_VALGRIND_DIR` to a complete compatible installation.
- Use Valgrind's own debug output to identify its core directory when `VALGRIND_LIB` is wrong.
- Load `cray-mrnet` or set `MRNET_INSTALL_DIR` when the frontend warns that the MRNet install location is absent.

Keep the frontend, daemon, starter, filter library, Valgrind core, CTI, and MRNet from a compatible installation set. Mixing module versions can pass path discovery and still fail during staging, dynamic linking, or protocol setup.

### Report contains external-library noise

The installed default suppression set filters known MPI, PMI, libcxi, libfabric, and miscellaneous runtime findings. For diagnosis:

```bash
# Ignore built-in suppressions for one launch.
export VALGRIND4HPC_IGNORE_SUPPRESSIONS=1

# Ask valgrind4hpc to write candidate rules.
valgrind4hpc --gen-suppressions-file=generated.supp <executable>

# Apply an explicit suppression file.
valgrind4hpc --suppressions=generated.supp <executable>
```

Review generated rules before adding them to the product. A suppression should remove a known external false positive or accepted runtime behavior, not conceal a defect in the target application or parser.

### Inspect one subset of ranks

Use `--from-ranks` to reduce a report to the suspected ranks without changing the size of the launched job:

```bash
valgrind4hpc -n 16 --from-ranks=0-3,8 <executable>
```

Use `--outputfile=<path>` when the report must survive terminal or scheduler-log truncation.

### Stop on an error and attach a debugger

`--vgdb-error=<count>` asks Valgrind to stop after the selected error count. valgrind4hpc prints the rank-specific VGDB and GDB4HPC attachment instructions. This path requires direct SSH access to the target compute nodes; follow the generated paths and job identifier rather than copying values from another run.

## 7. SME directory

- **Andrew D'Angelo**
  - Contact: `andrew.dangelo@hpe.com`
- **John Leroy Vogt**
  - Contact: `john.leroy.vogt@hpe.com`

## 8. Reference Links

### Repository references

- [`doc/guides/user_guide.md`](guides/user_guide.md) - end-user examples for rank aggregation, WLM arguments, tools, suppressions, and VGDB.
- [`doc/man/valgrind4hpc.1.md`](man/valgrind4hpc.1.md) - command-line contract and target-build requirements.
- [`configure.ac`](../configure.ac) - dependency checks, coverage flags, and generated Makefiles.
- [`src/Makefile.am`](../src/Makefile.am) - shipped executables, library, and link dependencies.
- [`tests/unit/Makefile.am`](../tests/unit/Makefile.am) - unit-test composition.
- [`tests/function/README.md`](../tests/function/README.md) - functional harness entry points.
- [`tests/function/test_tool_config.yaml`](../tests/function/test_tool_config.yaml) - modules, WLM arguments, and host-specific functional-test settings.
- [`rpmbuild/SPECS/valgrind4hpc.spec`](../rpmbuild/SPECS/valgrind4hpc.spec) - installed package contents and lifecycle scripts.
- [`release_versioning`](../release_versioning) - product and ABI version policy.

=======================================================================
## [unreleased]
=======================================================================

### Bug Fixes

* CPE-9080: Fix output file path  [f32b562]

### Features

* Remove dependence on cdst-support (#227)  [52ac410]

=======================================================================
## [2.13.5]
=======================================================================

### Features

* CPE-7743: Update Valgrind to 3.24  [74174f2]
* Build with g++14 on rhel 9.5 and sles15sp6 (#221)  [f4e5ef0]
* Add rhel 9.5, remove rhel 8.9 and sles15sp4 (#220)  [1680c02]
* CPE-6037: Add source code to user guide (#219)  [ed80843]

=======================================================================
## [2.13.4]
=======================================================================

### Bug Fixes

* PE-54291: Finish analysis early if job exited unexpectedly  [3185acb]

### Features

* Support rhel 8.10 (#218)  [f0f08f0]
* Support rhel 8.10  [43ae95e]
* Add builds for rhel 9.4 and sles15sp6 (#217)  [77bc16e]
* PE-54471: Add suppressions for aarch64 libcxi  [ab836fd]
* PE-55037: Remove deprecated exp-sgcheck tool support  [4d73c64]

=======================================================================
## [2.13.3]
=======================================================================

### Bug Fixes

* PE-51571: Parse arguments before starting network  [32f7309]

### Features

* PE-51960: Added support for rhel89/93 & gcc13  [1deb26a]
* Update Valgrind to 3.22, support syscall userfaultfd  [5fe746b]
* Build with gcc toolset 12 on redhat (PE-49713)  [521a267]

=======================================================================
## [2.13.1]
=======================================================================

### Features

* PE-47184: Add valgrind4hpc user guide (#198)  [40e1503]
* Use native compilers on sles (#196)  [83801c4]

=======================================================================
## [2.13.0]
=======================================================================

### Bug Fixes

* PE-45205: Fix --from-ranks filtering and suppression generation  [f9fa1f0]
* Fix install path exported by lmod modulefile on relocated install (#184)  [2373ca8]

### Features

* Build with gcc-toolset-10 on redhat  [850388a]
* PE-45055: Add GDB4hpc connection functionality for VGDB mode  [9ea02f6]

=======================================================================
## [2.12.11]
=======================================================================

### Features

* PE-44991: Update Valgrind to 3.20 and add VGDB option support  [be48a41]

=======================================================================
## [2.12.10]
=======================================================================

### Bug Fixes

* Monitor valgrind process for stop signals and start it again if it encounters any (#157) - PE-35799  [ef4e802]

### Features

* Added support for rhel86 - PE-41140 #158   [5c1dcd5]

=======================================================================
## [2.12.9]
=======================================================================

### Features

* Added support for sles15sp4 x86 - PE-40983 #155  [5ffec88]
* Added autogen changelog/release notes functionality - PE-40699 #153  [ebddfc0]

=======================================================================
## [2.12.8]
=======================================================================

### Features

* Added support for rhel85 - PE-40102 (#150)  [e135dad]


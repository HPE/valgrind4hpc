valgrind4hpc 2.13.7
================================================================================

Product Description
---------------------------
- Valgrind4hpc is a Valgrind-based debugging tool to aid in the detection of memory 
  leaks and errors in parallel applications. Valgrind4hpc aggregates any duplicate
  messages across ranks to help provide an understandable picture of
  program behavior. Valgrind4hpc manages starting and redirecting output from many
  copies of Valgrind, as well as deduplicating and filtering Valgrind messages.
  If your program can be debugged with Valgrind, it can be debugged with Valgrind4hpc.
  - SUSTAINING RELEASE NOTICE: Following the CPE 25.09 release, Valgrind4hpc
  will no longer be receiving feature updates. Valgrind4hpc will still be
  released as part of CPE, but may be removed in a future release.

Changelog
---------------------------

=======================================================================
## [2.14.0 Open Source]
=======================================================================

This is the first version released as open source.  There are a number
of change to make it buildable and runable outside of the HPE environment.

* Redid the build system to use meson.
* Removed dependence on enviromnent modules.
* Changed the install layout to a more standard form.
* Created a cray-mrnet subproject to remove the dependence on the
    cray-mrnet package.

=======================================================================
## [2.13.6 CPE Sustainment]
=======================================================================
 
### Bug Fixes
 
* CPE-9080: Fix output file path  
 
### Features
 
* Remove dependence on cdst-support 
 
=======================================================================
## [2.13.5]
=======================================================================
 
### Features
 
* CPE-7743: Update Valgrind to 3.24  
* Build with g++14 on rhel 9.5 and sles15sp6 
* Add rhel 9.5, remove rhel 8.9 and sles15sp4 
* CPE-6037: Add source code to user guide 
 
=======================================================================
## [2.13.4]
=======================================================================
 
### Bug Fixes
 
* PE-54291: Finish analysis early if job exited unexpectedly  
 
### Features
 
* Support rhel 8.10 
* Support rhel 8.10  
* Add builds for rhel 9.4 and sles15sp6 
* PE-54471: Add suppressions for aarch64 libcxi  
* PE-55037: Remove deprecated exp-sgcheck tool support  
 
=======================================================================
## [2.13.3]
=======================================================================
 
### Bug Fixes
 
* PE-51571: Parse arguments before starting network  
 
### Features
 
* PE-51960: Added support for rhel89/93 & gcc13  
* Update Valgrind to 3.22, support syscall userfaultfd  
* Build with gcc toolset 12 on redhat 
 
 

OS Dependencies
---------------------------
- HPE CSM systems with SLES 15 SP6 - SP7
- HPE HPCM systems with SLES 15 SP6 - SP7 or RHEL 8.10 - 9.5,9.6
- HPE Apollo systems with RHEL 8.10

Product Dependencies
---------------------------
- cray-mrnet (optional)
- cray-cti 

Documentation
---------------------------
- See man valgrind4hpc.

Installation Instructions
---------------------------
- rpm -ivh valgrind4hpc-2.13.7-0-.el9.x86_64.rpm

  To make valgrind4hpc 2.13.7 the default version of valgrind4hpc, execute:
  /opt/cray/pe/admin-pe/set_default_files/set_default_valgrind4hpc_2.13.7

Legal Notices
---------------------------
Certain components, files or programs contained within this package or product are Copyright 2010-2026 Hewlett Packard Enterprise Development LP. 

Attribution notices for open source licensed software for this package are detailed in the file:
  /opt/cray/pe/valgrind4hpc/2.13.7/ATTRIBUTIONS_valgrind4hpc.txt


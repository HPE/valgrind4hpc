# Packaging definitions
%global pkgversion           %(%{_sourcedir}/get_package_data --crayversion)
%global branch               %(%{_sourcedir}/get_package_data --branch)
%global pkgversion_separator -
%global copyright_date       %(date +%%Y)
%global copyright            Certain components, files or programs contained within this package or product are Copyright 2010-%{copyright_date} Hewlett Packard Enterprise Development LP.

# RPM build time
%global release_date %(date +%%B\\ %%Y)

%global product valgrind4hpc
%global cray_product %{product}
%global cray_name %{cray_product}

# Path definitions
%global cray_prefix /opt/cray/pe
%global test_prefix /opt/cray/tests

#FIXME: This should be relocatable
%global external_build_dir %{cray_prefix}/%{cray_product}/%{pkgversion}

%global tests_source_dir %{_topdir}/../tests

# modulefile definitions
%global modulefile_name      %{cray_name}
%global module_template_name %{modulefile_name}.module.template

# lmod modulefiles
%global lmod_template_valgrind4hpc template_%{cray_product}.lua

# set_default modulefile definitions
%global set_default_command        set_default
%global set_default_template       set_default_template
%global set_default_path           admin-pe/set_default_files

# This file is sourced by craype to resolve dependencies for products without
# loading modules.
%global cray_dependency_resolver set_pkgconfig_default_%{cray_name}
%global cray_dependency_resolver_template_name set_pkgconfig_default.template

# release notes
%global release_notes_file release_notes.md

# yaml file
%global yaml_template yaml.template
%global removal_date  %(date '+%Y-%m-%d' -d "+5 years")

# attributions file
%global attributions_name ATTRIBUTIONS_%{cray_name}.txt

# set default path file
%global set_paths_template_name set_paths_stub
%global set_paths_name .%{set_paths_template_name}

# dso list of files added to pe cache
%global cray_dso_list .cray_dynamic_file_list

# cdst-support version
%global cdst_support_pkgversion_min %(%{_sourcedir}/get_package_data --cdstversionmin)
%global cdst_support_pkgversion_max %(%{_sourcedir}/get_package_data --cdstversionmax)

# cti version
%global cti_pkgversion_min %(%{_sourcedir}/get_package_data --ctiversionmin)
%global cti_pkgversion_max %(%{_sourcedir}/get_package_data --ctiversionmax)

# mrnet version
%global mrnet_pkgversion_min %(%{_sourcedir}/get_package_data --mrnetversionmin)
%global mrnet_pkgversion_max %(%{_sourcedir}/get_package_data --mrnetversionmax)

# Disable debug package
%global debug_package %{nil}

# Disable build id links
%define _build_id_links none

# System strip command may be too old, use current path
%global __strip strip

# filter provides/requires
%global privlibs             libmrnet.*
%global privlibs %{privlibs}|libxplat.*
%global privlibs %{privlibs}|libvalgrind4hpc_filters.*
%global privlibs %{privlibs}|libstdc++.*
%global __provides_exclude ^(%{privlibs})\\.so*
%global __requires_exclude ^(%{privlibs})\\.so*

# set type of valgrind libs to include
%ifarch x86_64
%global archType 'amd64'
%global SYS_HW_TAG HARDWARE
%global SYS_WB_TAG WHITEBOX
%endif
%ifarch aarch64
%global archType 'arm64'
%global SYS_HW_TAG AARCH64
%global SYS_WB_TAG AARCH64
%endif
%if 0%{?rhel} == 8
%global OS_HW_TAG el8
%global OS_WB_TAG el8
%endif

# Dist tags for SuSE need to be manually set
%if 0%{?suse_version}
%if 0%{?sle_version} == 150400
%global dist .sles15sp4
%endif
%if 0%{?sle_version} == 150500
%global dist .sles15sp5
%endif
%global OS_HW_TAG 7.0
%global OS_WB_TAG sles15
%endif

Summary:    Parallel Valgrind Tool
Name:       %{cray_name}-%{pkgversion}
# BUILD_METADATA is set by Jenkins
Version:    %(echo ${BUILD_METADATA})
%if %{branch} == "release"
Release:    %(echo ${BUILD_NUMBER})%{dist}
%else
Release:    1%{dist}
%endif
Prefix:     %{cray_prefix}
License:    HPE Proprietary
Vendor:     Hewlett Packard Enterprise Development LP
Group:      Development/Tools/Debuggers
Provides:   %{cray_name} = %{pkgversion}
Requires:   set_default_3, cray-cdst-support >= %{cdst_support_pkgversion_min}, cray-cdst-support < %{cdst_support_pkgversion_max}, cray-cti >= %{cti_pkgversion_min}, cray-cti < %{cti_pkgversion_max}, cray-mrnet >= %{mrnet_pkgversion_min}, cray-mrnet < %{mrnet_pkgversion_max}
Source0:    %{module_template_name}
Source2:    %{cray_dependency_resolver_template_name}
Source3:    %{release_notes_file}
Source4:    %{attributions_name}
Source5:    %{set_paths_template_name}
Source6:    %{lmod_template_valgrind4hpc}
Source7:    %{yaml_template}

%description
Valgrind4hpc is a Valgrind-based debugging tool to aid in the detection of memory leaks and errors in parallel applications.

%package -n %{cray_name}-tests-%{pkgversion}
Summary:  valgrind4hpc functional tests
Group:    Development/Tools/Debuggers
Provides: %{cray_name}-tests = %{pkgversion}
Requires: %{cray_name} = %{pkgversion}

%description -n %{cray_name}-tests-%{pkgversion}
Functional tests for valgrind4hpc

%prep
# Run q(uiet) with build directory name, c(reate) subdirectory, disable T(arball) unpacking
%setup -q -n %{name} -c -T

%build
# external build
%{__sed} 's|<VERSION>|%{pkgversion}|g;s|<RELEASE>|%{version}-%{release}|g;s|<date>\.<REVISION>|%{version}|g;s|<COPYRIGHT>|%{copyright}|g;s|<NAME>|%{cray_name}|g;s|<CRAY_PREFIX>|%{cray_prefix}|g;s|<DIST>|%{dist}.%{_target_cpu}|g;s|<ARCH>|%{_target_cpu}|g;s|<ATTRIBUTIONS_FILE_PATH>|%{cray_prefix}/%{product}/%{pkgversion}/%{attributions_name}|g;s|<cdst_version_range>|>= %{cdst_support_pkgversion_min}, < %{cdst_support_pkgversion_max}|g;s|<cti_version_range>|>= %{cti_pkgversion_min}, < %{cti_pkgversion_max}|g;s|<mrnet_version_range>|>= %{mrnet_pkgversion_min}, < %{mrnet_pkgversion_max}|g' %{SOURCE3} > ${RPM_BUILD_DIR}/%{release_notes_file}
%{__sed} 's|<COPYRIGHT>|%{copyright}|g' %{SOURCE4} > ${RPM_BUILD_DIR}/%{attributions_name}
%{__sed} 's|<CRAY_NAME>|%{cray_name}|g' %{SOURCE5} > ${RPM_BUILD_DIR}/%{set_paths_name}

%install
# copy files from external install
#
# Cray PE package root
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}

# Information files
%{__cp} -a ${RPM_BUILD_DIR}/%{release_notes_file} ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/%{release_notes_file}
%{__cp} -a ${RPM_BUILD_DIR}/%{attributions_name} ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/%{attributions_name}

# Libraries
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/lib
%{__cp} -a %{external_build_dir}/lib/libvalgrind4hpc_filters.so ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/lib

# Libraries static
# pkg-config
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/lib/pkgconfig
%{__cp} -a %{external_build_dir}/lib/pkgconfig/valgrind.pc ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/lib/pkgconfig

# Headers
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/include
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/include/valgrind
%{__cp} -a %{external_build_dir}/include/valgrind/*.h ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/include/valgrind
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/include/valgrind/vki
%{__cp} -a %{external_build_dir}/include/valgrind/vki/*.h ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/include/valgrind/vki

# libexec binaries
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/libexec
%{__cp} -a %{external_build_dir}/libexec/valgrind4hpc_daemon ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/libexec
%{__cp} -a %{external_build_dir}/libexec/valgrind4hpc_starter ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/libexec
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/libexec/valgrind
%{__cp} -a %{external_build_dir}/libexec/valgrind/*-linux ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/libexec/valgrind
%{__cp} -a %{external_build_dir}/libexec/valgrind/*-linux.so ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/libexec/valgrind
%{__cp} -a %{external_build_dir}/libexec/valgrind/*.supp ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/libexec/valgrind

# Binaries
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/bin
%{__cp} -a %{external_build_dir}/bin/callgrind_annotate ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/bin
%{__cp} -a %{external_build_dir}/bin/callgrind_control ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/bin
%{__cp} -a %{external_build_dir}/bin/cg_annotate ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/bin
%{__cp} -a %{external_build_dir}/bin/cg_diff ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/bin
%{__cp} -a %{external_build_dir}/bin/cg_merge ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/bin
%{__cp} -a %{external_build_dir}/bin/ms_print ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/bin
%{__cp} -a %{external_build_dir}/bin/valgrind ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/bin
%{__cp} -a %{external_build_dir}/bin/valgrind4hpc ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/bin
%{__cp} -a %{external_build_dir}/bin/valgrind-di-server ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/bin
%{__cp} -a %{external_build_dir}/bin/valgrind-listener ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/bin
%{__cp} -a %{external_build_dir}/bin/vgdb ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/bin

# Share
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share

# manpages
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/man/man1
%{__cp} -a %{external_build_dir}/share/man/man1/callgrind_annotate.1 ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/man/man1
%{__cp} -a %{external_build_dir}/share/man/man1/callgrind_control.1 ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/man/man1
%{__cp} -a %{external_build_dir}/share/man/man1/cg_annotate.1 ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/man/man1
%{__cp} -a %{external_build_dir}/share/man/man1/cg_diff.1 ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/man/man1
%{__cp} -a %{external_build_dir}/share/man/man1/cg_merge.1 ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/man/man1
%{__cp} -a %{external_build_dir}/share/man/man1/ms_print.1 ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/man/man1
%{__cp} -a %{external_build_dir}/share/man/man1/valgrind.1 ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/man/man1
%{__cp} -a %{external_build_dir}/share/man/man1/valgrind4hpc.1 ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/man/man1
%{__cp} -a %{external_build_dir}/share/man/man1/valgrind-listener.1 ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/man/man1
%{__cp} -a %{external_build_dir}/share/man/man1/vgdb.1 ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/man/man1

# other documentation
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/guides
%{__cp} -a %{external_build_dir}/share/guides/user_guide.md ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/guides

# suppressions
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/suppressions
%{__cp} -a %{external_build_dir}/share/suppressions/known.supp ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/suppressions
%{__cp} -a %{external_build_dir}/share/suppressions/libmpich_cray.supp ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/suppressions
%{__cp} -a %{external_build_dir}/share/suppressions/libpmi.supp ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/suppressions
%{__cp} -a %{external_build_dir}/share/suppressions/misc.supp ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/share/suppressions

# modulefile
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/modulefiles/%{modulefile_name}
%{__sed} 's|<PREFIX>|%{external_build_dir}|g;s|<CRAY_NAME>|%{cray_name}|g;s|<VERSION>|%{pkgversion}|g;s|<COPYRIGHT>|%{copyright}|g' %{SOURCE0} > ${RPM_BUILD_ROOT}/%{prefix}/modulefiles/%{modulefile_name}/%{pkgversion}

# lmod modulefile
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/lmod/modulefiles/core/%{cray_product}
%{__sed} 's|\[@%PREFIX_PATH%@\]|%{prefix}|g;s|\[@%MODULE_VERSION%@\]|%{pkgversion}|g;s|<COPYRIGHT>|%{copyright}|g' %{SOURCE6} > ${RPM_BUILD_ROOT}/%{prefix}/lmod/modulefiles/core/%{cray_product}/%{pkgversion}.lua

# Cray PE dependency resolver
%{__sed} 's|<CRAY_PREFIX>|%{cray_prefix}|g;s|<PKG_VERSION>|%{pkgversion}|g;s|<PE_PRODUCT>|%{cray_product}|g' %{SOURCE2} > ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/%{cray_dependency_resolver}
%{__cp} -a ${RPM_BUILD_DIR}/%{set_paths_name} ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/%{set_paths_name}

# set_default template
%{__sed} 's|\[product_name\]|%{cray_product}|g;s|\[version_string\]|%{pkgversion}|g;s|\[install_dir\]|%{prefix}|g;s|\[module_dir\]|%{prefix}/modulefiles|g;s|\[module_name_list\]|%{modulefile_name}|g;s|\[lmod_dir_list\]|%{prefix}/lmod/modulefiles/core|g;s|\[lmod_name_list\]|%{modulefile_name}|g' %{_sourcedir}/set_default/%{set_default_template} > ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/%{set_default_command}_%{cray_product}_%{pkgversion}

# set_default into admin-pe
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{set_default_path}
%{__install} -D ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/%{set_default_command}_%{cray_product}_%{pkgversion} ${RPM_BUILD_ROOT}/%{prefix}/%{set_default_path}/%{set_default_command}_%{cray_product}_%{pkgversion}
%{__mkdir} -p %{_rpmdir}/%{_arch}

# yaml file
%global start_rmLine %(sed -n /section-3/= %{SOURCE7})
%global end_rmLine %(sed -n /admin-pe/= %{SOURCE7} | tail -1)
%global tests_rpm_name %{cray_name}-tests-%{pkgversion}-%{version}-%{release}.%{_arch}
%global rpm_list %{tests_rpm_name}.rpm
%if %{branch} == "release"
%{__sed} 's|<PRODUCT>|%{cray_product}|g;s|<VERSION>|%{pkgversion}|g;s|<BUILD_METADATA>|%{version}|g;s|<RELEASE>|%{release}|g;s|<ARCH>|%{_arch}|g;s|<REMOVAL_DATE>|%{removal_date}|g;s|<SYS_HW_TAG>|%{SYS_HW_TAG}|g;s|<SYS_WB_TAG>|%{SYS_WB_TAG}|g;s|<OS_HW_TAG>|%{OS_HW_TAG}|g;s|<OS_WB_TAG>|%{OS_WB_TAG}|g;s|<RPM_LST>|%{rpm_list}|g;s|<TESTS_RPM_NAME>|%{tests_rpm_name}|g;s|<SET_DEFAULT_VALUE>|1|g' %{SOURCE7} > %{_rpmdir}/%{_arch}/%{cray_product}-%{pkgversion}-%{version}-%{release}.%{_arch}.rpm.yaml
%else
%{__sed} '%{start_rmLine},%{end_rmLine}d;s|section-5|section-3|g;s|<PRODUCT>|%{cray_product}|g;s|<VERSION>|%{pkgversion}|g;s|<BUILD_METADATA>|%{version}|g;s|<RELEASE>|%{release}|g;s|<ARCH>|%{_arch}|g;s|<REMOVAL_DATE>|%{removal_date}|g;s|<SYS_HW_TAG>|%{SYS_HW_TAG}|g;s|<SYS_WB_TAG>|%{SYS_WB_TAG}|g;s|<OS_HW_TAG>|%{OS_HW_TAG}|g;s|<OS_WB_TAG>|%{OS_WB_TAG}|g;s|<RPM_LST>|%{rpm_list}|g;s|<TESTS_RPM_NAME>|%{tests_rpm_name}|g;s|<SET_DEFAULT_VALUE>|0|g' %{SOURCE7} > %{_rpmdir}/%{_arch}/%{cray_product}-%{pkgversion}-%{version}-%{release}.%{_arch}.rpm.yaml
%endif

# tests
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests
%{__cp} -a %{tests_source_dir}/function/avocado_config.yaml    ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/avocado_config.yaml
%{__cp} -a %{tests_source_dir}/function/Makefile               ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/Makefile
%{__cp} -a %{tests_source_dir}/function/cdst-test/test_tool.py ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/test_tool.py
%{__cp} -a %{tests_source_dir}/function/test_tool_config.yaml  ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/test_tool_config.yaml
%{__cp} -a %{tests_source_dir}/function/tests.py               ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py
%{__cp} -a %{tests_source_dir}/function/README.md              ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/README.md
                 
%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/README.md                   ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/README.md
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/README_config.md            ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/README_config.md
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/README_textcheck.md         ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/README_textcheck.md
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/__init__.py                 ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/__init__.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/artifactory.py              ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/artifactory.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/config.py                   ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/config.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/config_default.py           ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/config_default.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/config_nodes.py             ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/config_nodes.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/env.py                      ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/env.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/files.py                    ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/files.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/job_environment.py          ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/job_environment.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/log.py                      ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/log.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/modules.py                  ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/modules.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/remote_test_tool_startup.py ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/remote_test_tool_startup.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/remote_test_tool_ui.py      ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/remote_test_tool_ui.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/ssh.py                      ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/ssh.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/test_server.py              ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/test_server.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/test_server_commands.py     ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/test_server_commands.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/test_server_proto.py        ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/test_server_proto.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/textcheck.py                ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/textcheck.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/useful.py                   ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/useful.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/bootstrap.py                ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/bootstrap.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/requirements.txt            ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/requirements.txt

%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/data
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/data/hosts.yaml    ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/data/hosts.yaml
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/data/products.yaml ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/data/products.yaml

%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/scripts
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/scripts/avo_config.py        ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/scripts/avo_config.py
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/scripts/passwordedscp.expect ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/scripts/passwordedscp.expect
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/scripts/passwordedssh.expect ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/scripts/passwordedssh.expect
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/scripts/sshcopyid.expect     ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/scripts/sshcopyid.expect
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/scripts/uai.expect           ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/scripts/uai.expect
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/scripts/validate_ssh.sh      ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/scripts/validate_ssh.sh

%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/src
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/src/Makefile    ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/src/Makefile
%{__cp} -a %{tests_source_dir}/function/cdst-test/cdst_test/src/hello_mpi.c ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/src/hello_mpi.c

%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src
%{__cp} -a %{tests_source_dir}/function/src/Makefile                          ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/Makefile
%{__cp} -a %{tests_source_dir}/function/src/mpi_illegal_free_calloc.c         ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_illegal_free_calloc.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_illegal_free_malloc.c         ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_illegal_free_malloc.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_illegal_free_realloc_grow.c   ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_illegal_free_realloc_grow.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_illegal_free_realloc_shrink.c ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_illegal_free_realloc_shrink.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_illegal_free_stack.c          ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_illegal_free_stack.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_mem_leak_calloc.c             ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_mem_leak_calloc.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_mem_leak_malloc.c             ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_mem_leak_malloc.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_mem_leak_realloc_grow.c       ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_mem_leak_realloc_grow.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_mem_leak_realloc_shrink.c     ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_mem_leak_realloc_shrink.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_no_error.c                    ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_no_error.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_oob_read_calloc.c             ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_read_calloc.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_oob_read_malloc.c             ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_read_malloc.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_oob_read_mpi.c                ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_read_mpi.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_oob_read_realloc_grow.c       ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_read_realloc_grow.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_oob_read_realloc_shrink.c     ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_read_realloc_shrink.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_oob_write_calloc.c            ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_write_calloc.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_oob_write_malloc.c            ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_write_malloc.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_oob_write_mpi.c               ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_write_mpi.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_oob_write_realloc_grow.c      ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_write_realloc_grow.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_oob_write_realloc_shrink.c    ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_write_realloc_shrink.c
%{__cp} -a %{tests_source_dir}/function/src/mpi_sanity_check.c                ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_sanity_check.c
%{__cp} -a %{tests_source_dir}/function/src/shmem_double_free.c               ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/shmem_double_free.c
%{__cp} -a %{tests_source_dir}/function/src/shmem_no_error.c                  ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/shmem_no_error.c
%{__cp} -a %{tests_source_dir}/function/src/shmem_oob_read.c                  ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/shmem_oob_read.c
%{__cp} -a %{tests_source_dir}/function/src/shmem_oob_write.c                 ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/shmem_oob_write.c
%{__cp} -a %{tests_source_dir}/function/src/shmem_sanity_check.c              ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/src/shmem_sanity_check.c

%{__install} -d ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data
%{__cp} -a %{tests_source_dir}/function/tests.py.data/any_summary.txt   ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data/any_summary.txt
%{__cp} -a %{tests_source_dir}/function/tests.py.data/no_error.txt      ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data/no_error.txt
%{__cp} -a %{tests_source_dir}/function/tests.py.data/leak.txt.template ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data/leak.txt.template
%{__cp} -a %{tests_source_dir}/function/tests.py.data/nonexistent.txt   ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data/nonexistent.txt
%{__cp} -a %{tests_source_dir}/function/tests.py.data/nonzero_error.txt ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data/nonzero_error.txt
%{__cp} -a %{tests_source_dir}/function/tests.py.data/illegal_free.txt  ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data/illegal_free.txt
%{__cp} -a %{tests_source_dir}/function/tests.py.data/oob_read.txt      ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data/oob_read.txt
%{__cp} -a %{tests_source_dir}/function/tests.py.data/oob_write.txt     ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data/oob_write.txt

# Touch the cray dynamic file list which will be populated/updated post-install
touch ${RPM_BUILD_ROOT}/%{prefix}/%{cray_product}/%{pkgversion}/%{cray_dso_list}

%post
# Add Shasta configuration files for PE content projection
if [ "${RPM_INSTALL_PREFIX}" = "%{cray_prefix}" ]; then
    mkdir -p /etc/%{cray_prefix}/admin-pe/bindmount.conf.d/
    mkdir -p /etc/%{cray_prefix}/admin-pe/modulepaths.conf.d/
    echo "%{cray_prefix}/%{product}/" > /etc/%{cray_prefix}/admin-pe/bindmount.conf.d/%{cray_name}.conf
    echo "%{cray_prefix}/modulefiles/%{modulefile_name}" > /etc/%{cray_prefix}/admin-pe/modulepaths.conf.d/%{modulefile_name}.conf
    echo "%{cray_prefix}/lmod/modulefiles/core/%{cray_name}" >> /etc/%{cray_prefix}/admin-pe/modulepaths.conf.d/%{modulefile_name}.conf
fi

# Process relocations
if [ "${RPM_INSTALL_PREFIX}" != "%{prefix}" ]
then
    # tcl modulefile
    %{__sed} -i "s|^\([[:space:]]*set VALGRIND4HPC_BASEDIR[[:space:]]*\)\(.*\)|\1${RPM_INSTALL_PREFIX}/%{cray_product}/%{pkgversion}|" ${RPM_INSTALL_PREFIX}/modulefiles/%{modulefile_name}/%{pkgversion}
    # lua modulefile
    %{__sed} -i "s|^\([[:space:]]*local INSTALL_ROOT[[:space:]]=*\)\(.*\)|\1= \"${RPM_INSTALL_PREFIX}\"|" ${RPM_INSTALL_PREFIX}/lmod/modulefiles/core/%{modulefile_name}/%{pkgversion}.lua

    echo "Warning: Relocatable valgrind4hpc might behave oddly due to valgrind requirements!"
else
    # Only call set_default if we are not relocating the rpm and there's not already a default set unless someone passes in CRAY_INSTALL_DEFAULT=1
    if [ ${CRAY_INSTALL_DEFAULT:-0} -eq 1 ] || [ ! -f ${RPM_INSTALL_PREFIX}/modulefiles/%{cray_product}/.version ]
    then
        ${RPM_INSTALL_PREFIX}/%{set_default_path}/%{set_default_command}_%{cray_product}_%{pkgversion}
    fi
fi

# Generate a list of dynamic shared objects (libraries) to add to Cray PE cache
echo "%{cray_prefix}/%{cray_product}/%{pkgversion}/libvalgrind4hpc_filters.so" > ${RPM_INSTALL_PREFIX}/%{cray_product}/%{pkgversion}/%{cray_dso_list}

# run ldconfig for good measure
if [ -w /etc/ld.so.cache ]
then
    if [[ ${RPM_INSTALL_PREFIX} = "%{cray_prefix}" ]]
    then
        /sbin/ldconfig
    fi
fi

%preun
default_link="${RPM_INSTALL_PREFIX}/%{cray_product}/default"

# Cleanup module .version if it points to this version
if [ -f ${RPM_INSTALL_PREFIX}/modulefiles/%{modulefile_name}/.version ]
then
  dotversion=`grep ModulesVersion ${RPM_INSTALL_PREFIX}/modulefiles/%{modulefile_name}/.version | cut -f2 -d'"'`

  if [ "$dotversion" == "%{pkgversion}" ]
  then
    %{__rm} -f ${RPM_INSTALL_PREFIX}/modulefiles/%{modulefile_name}/.version
    echo "Uninstalled version and .version file match = ${default_version}."
    echo "Removing %{modulefile_name} .version file."
    %{__rm} -f ${default_link}
  fi
fi


%postun
if [ $1 == 1 ]
then
  exit 0
fi

# If the install dir exists
if [[ -z `ls ${RPM_INSTALL_PREFIX}/%{cray_product}` ]]; then
  %{__rm} -rf ${RPM_INSTALL_PREFIX}/%{cray_product}
  if [ -f /etc%{prefix}/admin-pe/bindmount.conf.d/%{cray_name}.conf ]; then
    %{__rm} -rf /etc%{prefix}/admin-pe/bindmount.conf.d/%{cray_name}.conf
  fi
  if [ -f /etc%{prefix}/admin-pe/modulepaths.conf.d/%{cray_name}.conf ]; then
    %{__rm} -rf /etc%{prefix}/admin-pe/modulepaths.conf.d/%{cray_name}.conf
  fi
  if [ -d ${RPM_INSTALL_PREFIX}/lmod/modulefiles/core/%{cray_name} ]; then
    %{__rm} -rf ${RPM_INSTALL_PREFIX}/lmod/modulefiles/core/%{cray_name}
  fi
  if [ -d ${RPM_INSTALL_PREFIX}/modulefiles/%{cray_name} ]; then
    %{__rm} -rf ${RPM_INSTALL_PREFIX}/modulefiles/%{cray_name}
  fi
fi

# run ldconfig for good measure
if [ -w /etc/ld.so.cache ]
then
    if [[ ${RPM_INSTALL_PREFIX} = "%{cray_prefix}" ]]
    then
        /sbin/ldconfig
    fi
fi

%files
%defattr(755, root, root)
%dir %{prefix}/%{cray_product}/%{pkgversion}
%dir %{prefix}/%{cray_product}/%{pkgversion}/lib
%dir %{prefix}/%{cray_product}/%{pkgversion}/lib/pkgconfig
%dir %{prefix}/%{cray_product}/%{pkgversion}/include
%dir %{prefix}/%{cray_product}/%{pkgversion}/include/valgrind
%dir %{prefix}/%{cray_product}/%{pkgversion}/include/valgrind/vki
%dir %{prefix}/%{cray_product}/%{pkgversion}/libexec
%dir %{prefix}/%{cray_product}/%{pkgversion}/libexec/valgrind
%dir %{prefix}/%{cray_product}/%{pkgversion}/bin
%dir %{prefix}/%{cray_product}/%{pkgversion}/share
%dir %{prefix}/%{cray_product}/%{pkgversion}/share/man
%dir %{prefix}/%{cray_product}/%{pkgversion}/share/man/man1
%dir %{prefix}/%{cray_product}/%{pkgversion}/share/suppressions
%dir %{prefix}/%{cray_product}/%{pkgversion}/share/guides
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/%{release_notes_file}
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/%{attributions_name}
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/lib/libvalgrind4hpc_filters.so
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/libexec/valgrind/*-%{archType}-linux
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/libexec/valgrind/*.supp
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/libexec/valgrind/*.so
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/lib/pkgconfig/valgrind.pc
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/include/valgrind/*.h
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/include/valgrind/vki/*.h
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/libexec/valgrind4hpc_daemon
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/libexec/valgrind4hpc_starter
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/bin/callgrind_annotate
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/bin/callgrind_control
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/bin/cg_annotate
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/bin/cg_diff
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/bin/cg_merge
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/bin/ms_print
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/bin/valgrind
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/bin/valgrind4hpc
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/bin/valgrind-di-server
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/bin/valgrind-listener
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/bin/vgdb
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/share/man/man1/*.1
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/share/suppressions/*.supp
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/share/guides/*
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/%{cray_dependency_resolver}
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/%{set_paths_name}
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/%{set_default_command}_%{cray_product}_%{pkgversion}
%attr(755, root, root) %{prefix}/%{set_default_path}/%{set_default_command}_%{cray_product}_%{pkgversion}
%attr(755, root, root) %{prefix}/modulefiles/%{modulefile_name}/%{pkgversion}
%attr(644, root, root) %{prefix}/lmod/modulefiles/core/%{cray_product}/%{pkgversion}.lua
%attr(644, root, root) %verify(not md5 size mtime) %{prefix}/%{cray_product}/%{pkgversion}/%{cray_dso_list}

%files -n %{cray_name}-tests-%{pkgversion}
%dir %{prefix}/%{cray_product}/%{pkgversion}/tests
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/avocado_config.yaml
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/Makefile
%attr(755, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/test_tool.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/test_tool_config.yaml
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/README.md
                 
%dir %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/README.md
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/README_config.md
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/README_textcheck.md
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/__init__.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/artifactory.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/config.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/config_default.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/config_nodes.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/env.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/files.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/job_environment.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/log.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/modules.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/remote_test_tool_startup.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/remote_test_tool_ui.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/ssh.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/test_server.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/test_server_commands.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/test_server_proto.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/textcheck.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/useful.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/bootstrap.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/requirements.txt

%dir %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/data
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/data/hosts.yaml
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/data/products.yaml

%dir %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/scripts
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/scripts/avo_config.py
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/scripts/passwordedscp.expect
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/scripts/passwordedssh.expect
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/scripts/sshcopyid.expect
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/scripts/uai.expect
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/scripts/validate_ssh.sh

%dir %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/src
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/src/Makefile
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/cdst_test/src/hello_mpi.c

%dir %{prefix}/%{cray_product}/%{pkgversion}/tests/src
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/Makefile
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_illegal_free_calloc.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_illegal_free_malloc.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_illegal_free_realloc_grow.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_illegal_free_realloc_shrink.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_illegal_free_stack.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_mem_leak_calloc.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_mem_leak_malloc.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_mem_leak_realloc_grow.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_mem_leak_realloc_shrink.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_no_error.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_read_calloc.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_read_malloc.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_read_mpi.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_read_realloc_grow.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_read_realloc_shrink.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_write_calloc.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_write_malloc.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_write_mpi.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_write_realloc_grow.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_oob_write_realloc_shrink.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/mpi_sanity_check.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/shmem_double_free.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/shmem_no_error.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/shmem_oob_read.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/shmem_oob_write.c
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/src/shmem_sanity_check.c

%dir %{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data/any_summary.txt
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data/no_error.txt
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data/leak.txt.template
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data/nonexistent.txt
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data/nonzero_error.txt
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data/illegal_free.txt
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data/oob_read.txt
%attr(644, root, root) %{prefix}/%{cray_product}/%{pkgversion}/tests/tests.py.data/oob_write.txt

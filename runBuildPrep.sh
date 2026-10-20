#!/bin/bash
#
# runBuildPrep.sh - Preps the build environment
#
# Copyright 2019-2023 Hewlett Packard Enterprise Development LP.
#
# Unpublished Proprietary Information.
# This unpublished work is protected to trade secret, copyright and other laws.
# Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
# no part of this work or its content may be used, reproduced or disclosed
# in any form.
#

source ./external/cdst_build_library/build_lib

echo "############################################"
echo "#             Installing deps              #"
echo "############################################"
target_pm=$(get_pm)
target_os=$(get_os)
target_arch=$(get_arch)
if [[ "$target_pm" == "$cdst_pm_zypper" ]]; then
   if [[ "$target_arch" == "$cdst_arch_x86_64" ]]; then
      sudo zypper refresh -f
   fi
   # Install zypper based dependencies
    zypper --non-interactive install \
        autoconf \
        autoconf-archive \
        automake \
        binutils \
        binutils-devel \
        bison \
        bzip2 \
        ctags \
        docbook-xsl-stylesheets \
        flex \
        libbz2-devel \
        liblzma5 \
        libtool \
        m4 \
        make \
        make-lang \
        makeinfo \
        mksh \
        ncurses \
        ncurses-devel \
        rpm-build \
        tcl \
        xsltproc \
        xz-devel \
        python3-pip \
        zlib-devel
    check_exit_status
elif [[ "$target_pm" == "$cdst_pm_yum" ]]; then
    if [[ "$target_os" == "$cdst_os_centos8" ]]; then
      # Note the following will be different on build VMs vs DST. Errors are okay.
      yum config-manager --set-enabled powertools
    fi
    # Install yum based components
    yum --assumeyes install \
        autoconf \
        automake \
        binutils \
        binutils-devel \
        bison \
        bzip2 \
        bzip2-devel \
        ctags \
        docbook-style-xsl \
        environment-modules \
        flex \
        libtool \
        libxslt \
        m4 \
        make \
        ncurses \
        ncurses-devel \
        rpm-build \
        tcl \
        xz-devel \
        python3-pip \
        zlib-devel
    check_exit_status

    if [[ "$target_arch" == "$cdst_arch_aarch64" && "$target_os" == "$cdst_os_rhel84" ]]; then
      yum --assumeyes install \
      https://arti.hpc.amslabs.hpecorp.net/artifactory/hpe-rhel-remote/EL8/Update4/GA/CRB/os/Packages/autoconf-archive-2018.03.13-1.el8.noarch.rpm \
      https://arti.hpc.amslabs.hpecorp.net/artifactory/hpe-rhel-remote/EL8/Update4/GA/CRB/os/Packages/perl-Unicode-EastAsianWidth-1.33-13.el8.noarch.rpm \
      https://arti.hpc.amslabs.hpecorp.net/artifactory/mirror-centos8/PowerTools/aarch64/os/Packages/texinfo-6.5-6.el8.aarch64.rpm
    else
      yum --assumeyes install \
            autoconf-archive \
            texinfo
    fi
    check_exit_status
else
    # Unknown OS! Exit with error.
    echo "Unsupported Package Manager detected!"
    exit 1
fi

# Install the common PE components
install_common_pe

# Install CTI, CDST support, and MRNet
install_cti
check_exit_status

install_mrnet
check_exit_status

capture_jenkins_build
check_exit_status

echo "############################################"
echo "#          Done with build prep            #"
echo "############################################"

exit_with_status

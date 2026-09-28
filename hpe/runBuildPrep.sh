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

# directory of this script
hpe="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source "$hpe/external/cdst_build_library/build_lib"


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
        meson \
        libboost_headers1_66_0-devel \
        ncurses \
        ncurses-devel \
        rpm-build \
        tcl \
        xsltproc \
        xz-devel \
        python3-pip \
        python311 \
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
        boost-devel \
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
        python3.11 \
        zlib-devel \
        autoconf-archive \
        texinfo
    check_exit_status
else
    # Unknown OS! Exit with error.
    echo "Unsupported Package Manager detected!"
    exit 1
fi

# Install the common PE components
install_common_pe

# Install CTI, CDST support, and MRNet
install_mrnet
check_exit_status

echo "############################################"
echo "#          Ensuring build system           #"
echo "############################################"

# meson requires python 3.7 or newer
python3.11 -m ensurepip --upgrade
check_exit_status

python3.11 -m pip install meson ninja --trusted-host https://arti.hpc.amslabs.hpecorp.net \
      --extra-index-url https://arti.hpc.amslabs.hpecorp.net:443/artifactory/api/pypi/dst-pip-master-local/simple \
      --index-url https://arti.hpc.amslabs.hpecorp.net:443/artifactory/api/pypi/pypi-remote/simple
check_exit_status

capture_jenkins_build
check_exit_status

echo "############################################"
echo "#          Done with build prep            #"
echo "############################################"

exit_with_status

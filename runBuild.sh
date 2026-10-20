#!/bin/bash
#
# runBuild.sh - Build steps for valgrind4hpc
#
# Copyright 2019-2022 Hewlett Packard Enterprise Development LP.
#
# Unpublished Proprietary Information.
# This unpublished work is protected to trade secret, copyright and other laws.
# Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
# no part of this work or its content may be used, reproduced or disclosed
# in any form.
#

echo "############################################"
echo "#            Setup environment.            #"
echo "############################################"

top_level=$PWD

source ./external/cdst_build_library/build_lib_gcc

setup_modules

module load cray-cdst-support
check_exit_status

module load cray-cti-devel
check_exit_status

module load cray-mrnet
check_exit_status

module list

# Create install directory
source $top_level/release_versioning
valgrind4hpc_version=
branch_name=$(get_branch_info)
branch_type=$(echo "$branch_name" | cut -d'/' -f1)
if [ "$branch_type" != "release" ]; then
  valgrind4hpc_version="$major.$minor.$revision.$build_number"
else
  valgrind4hpc_version="$major.$minor.$revision"
fi

install_dir="/opt/cray/pe/valgrind4hpc/$valgrind4hpc_version"
echo "Install dir: \"$install_dir\""

if [[ ! -z $BRANCH_NAME ]]; then
  echo "cleaning build env"
  rm -rf /opt/cray/pe/valgrind4hpc
fi

mkdir -p $install_dir
check_exit_status

echo "############################################"
echo "#            Building valgrind             #"
echo "############################################"

# ensure submodule is checked out
if [[ ! -f $top_level/external/valgrind/README ]]; then
    echo "valgrind submodule not checked out..."
    exit 1
fi

cd $top_level/external/valgrind
check_exit_status

./autogen.sh
check_exit_status

PERL="/usr/bin/perl" ./configure --prefix=$install_dir
check_exit_status

make $cdst_j_flags
check_exit_status

# build manpages
cd $top_level/external/valgrind/docs
check_exit_status

make $cdst_j_flags man-pages
check_exit_status

cd $top_level/external/valgrind
check_exit_status

make $cdst_j_flags install
check_exit_status

echo "############################################"
echo "#          Building valgrind4hpc           #"
echo "############################################"

cd $top_level
check_exit_status

autoreconf -ifv
check_exit_status

./configure --prefix=$install_dir --with-boost=$CRAY_CDST_SUPPORT_INSTALL_DIR --with-boost-libdir=$CRAY_CDST_SUPPORT_INSTALL_DIR/lib
check_exit_status

make $cdst_j_flags
check_exit_status

make $cdst_j_flags install
check_exit_status

# deliver documentation
mkdir -p $install_dir/share/guides
check_exit_status

cp ./doc/guides/*.md $install_dir/share/guides
check_exit_status

echo "############################################"
echo "#              Done with build             #"
echo "############################################"

exit_with_status

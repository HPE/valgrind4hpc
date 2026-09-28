#!/bin/bash
#
# runBuildPackage.sh - Package steps for valgrind4hpc
#
# Copyright 2019-2023 Hewlett Packard Enterprise Development LP.
#
# Unpublished Proprietary Information.
# This unpublished work is protected to trade secret, copyright and other laws.
# Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
# no part of this work or its content may be used, reproduced or disclosed
# in any form.
#

hpe="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source "$hpe/external/cdst_build_library/build_lib"

setup_modules

module load cray-cti-devel
check_exit_status

module load cray-mrnet
check_exit_status

echo "############################################"
echo "#          Generating Cpedocs              #"
echo "############################################"

# This doesn't deliver any documentation anywhere, it only tests the
# low bar that collect_cpedocs.sh still runs without an error.
pushd doc/cpedocs
./collect_cpedocs.sh
check_exit_status
popd

echo "############################################"
echo "#             Creating rpm                 #"
echo "############################################"
rpmbuilddir="$hpe/rpmbuild"
cd ${rpmbuilddir}
check_exit_status
rpmbuild -bb -D "_topdir ${rpmbuilddir}" SPECS/valgrind4hpc.spec
check_exit_status

echo "############################################"
echo "#          Done with packaging             #"
echo "############################################"

exit_with_status

#
# cray_extensions.m4 Cray configure extensions.
#
# Copyright 2015-2019,2020-2021 Hewlett Packard Enterprise Development LP.
#
# Unpublished Proprietary Information.
# This unpublished work is protected to trade secret, copyright and other laws.
# Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
# no part of this work or its content may be used, reproduced or disclosed
# in any form.
#

AC_DEFUN([cray_INIT],
[
	dnl Pull in the revision information from the $PWD/release_versioning file
	m4_define([VALGRIND4HPC_REVISION], [m4_esyscmd_s([source $PWD/release_versioning; echo "$revision"])])

	m4_define([VALGRIND4HPC_MAJOR], [m4_esyscmd_s([source $PWD/release_versioning; echo "$major"])])
	m4_define([VALGRIND4HPC_MINOR], [m4_esyscmd_s([source $PWD/release_versioning; echo "$minor"])])

	AC_SUBST([VALGRIND4HPC_RELEASE_VERSION], [VALGRIND4HPC_MAJOR.VALGRIND4HPC_MINOR.VALGRIND4HPC_REVISION])
])

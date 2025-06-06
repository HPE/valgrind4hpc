#
# configure.ac script for valgrind4hpc.
#
# Copyright 2015-2019,2020-2021 Hewlett Packard Enterprise Development LP.
#
# Unpublished Proprietary Information.
# This unpublished work is protected to trade secret, copyright and other laws.
# Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
# no part of this work or its content may be used, reproduced or disclosed
# in any form.
#

AC_PREREQ(2.63)

m4_include([m4/cray_extensions.m4])

dnl We need to use the m4_esyscmd here because the Cray macro extensions are
dnl not pulled in until after AC_INIT.
dnl This is not portable due to tr -d and source...
AC_INIT([valgrind4hpc], m4_esyscmd([source $PWD/release_versioning; echo $major.$minor | tr -d '\n']))

AC_COPYRIGHT([Copyright 2015-2019,2020-2021 Hewlett Packard Enterprise Development LP.])

AC_CONFIG_SRCDIR([src/valgrind4hpc_FE.C])
AC_CONFIG_AUX_DIR([config])
AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_HEADERS([config.h])

AC_SUBST([VALGRIND4HPC_DIR], ["$(cd $srcdir && pwd)"])

dnl Turn on Posix extensions
AC_USE_SYSTEM_EXTENSIONS

AM_INIT_AUTOMAKE([foreign -Wall])
LT_INIT

dnl Pull in Cray specific m4 extensions
cray_INIT

m4_ifdef([AM_SILENT_RULES], [AM_SILENT_RULES([yes])])

dnl Enable gcov code coverage if using --enable-code-coverage
AX_CODE_COVERAGE
AC_SUBST(CODE_COVERAGE_CPPFLAGS)
AC_SUBST(CODE_COVERAGE_CFLAGS)
AC_SUBST(CODE_COVERAGE_CXXFLAGS)
AC_SUBST(CODE_COVERAGE_LDFLAGS)
AC_SUBST(CODE_COVERAGE_LIBS)

###########################
### Check for programs. ###
###########################
AC_LANG(C++)
AM_PROG_AR
AC_PROG_CXX
AC_PROG_CXXCPP
AC_PROG_CXX_C_O
AC_PROG_CC
AC_PROG_INSTALL
AC_PROG_LIBTOOL
AC_PROG_LN_S
AC_PROG_SED

AX_CHECK_COMPILE_FLAG([-std=c++17], [
                        CXXFLAGS="$CXXFLAGS -Wall -std=c++17"])

############################
### Optional build deps  ###
############################

dnl
dnl Check for pkg-config
dnl
PKG_PROG_PKG_CONFIG

dnl This macro runs check for --with-libboost
AX_BOOST_BASE([1.69],, [AC_MSG_ERROR([valgrind4hpc needs libboost >=1.69, but it was not found in your system])])
LDFLAGS="$LDFLAGS $BOOST_LDFLAGS"
CPPFLAGS="$CPPFLAGS $BOOST_CPPFLAGS"
CXXFLAGS="$CXXFLAGS $BOOST_CPPFLAGS"

#####################################
### Check for pkg-config modules. ###
#####################################

dnl Check for CTI
PKG_CHECK_MODULES([CRAY_CTI_FE],[common_tools_fe],[],[AC_MSG_ERROR([libcommontools_fe.so not found.])])
PKG_CHECK_MODULES([CRAY_CTI_BE],[common_tools_be],[],[AC_MSG_ERROR([libcommontools_be.so not found.])])
dnl Add cdst support flags
#LDFLAGS="$LDFLAGS $CDST_SUP_LIBS"
#CFLAGS="$CFLAGS $CDST_SUP_CFLAGS"
#CXXFLAGS="$CXXFLAGS $CDST_SUP_CFLAGS"

dnl Check for MRNet
PKG_CHECK_MODULES([CRAY_MRNET], [cray-mrnet])

############################
### Check for libraries. ###
############################

dnl Check for MRNet
save_LDFLAGS="$LDFLAGS"
LDFLAGS="$LDFLAGS $CRAY_MRNET_LIBS"
AX_CXX_CHECK_LIB(   [mrnet],
                    [MRN::XTNetwork],
                    [AC_DEFINE( [HAVE_MRNET],
                                [1],
                                [Define to 1 if you have the mrnet library (-lmrnet).]
                            )
                    ],
                    [AC_MSG_ERROR([libmrnet not found.])]
                    )
dnl restore flags
LDFLAGS="$save_LDFLAGS"

###############################
### Check for header files. ###
###############################

AC_CHECK_HEADERS([arpa/inet.h fcntl.h netdb.h netinet/in.h stdlib.h string.h sys/socket.h sys/time.h unistd.h])

dnl Check for mrnet headers
save_CXXFLAGS="$CXXFLAGS"
CXXFLAGS="$CXXFLAGS $CRAY_MRNET_CFLAGS"
AC_CHECK_HEADER([mrnet/MRNet.h],
        [],
        [AC_MSG_FAILURE([mrnet/MRNet.h not found.])],
        []
        )
dnl restore flags
CXXFLAGS="$save_CXXFLAGS"

#####################################################################
### Check for typedefs, structures, and compiler characteristics. ###
#####################################################################
AC_HEADER_STDBOOL
AC_C_INLINE
AC_TYPE_INT64_T
AC_TYPE_PID_T
AC_TYPE_SIZE_T
AC_TYPE_SSIZE_T
AC_TYPE_UINT64_T

####################################
### Check for library functions. ###
####################################
AC_FUNC_FORK
AC_FUNC_MALLOC
AC_CHECK_FUNCS([clock_gettime dup2 gettimeofday inet_ntoa memset select setenv socket strchr strdup strerror])

################
### Finalize ###
################
AC_CONFIG_FILES([	Makefile
					src/Makefile
					doc/man/Makefile
					suppressions/Makefile
					tests/Makefile
					tests/test_support/Makefile
					tests/unit/Makefile
])

AC_OUTPUT

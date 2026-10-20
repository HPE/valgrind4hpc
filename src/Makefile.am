#
# Makefile.am for valgrind4hpc components.
#
# Copyright 2015-2019,2020-2021 Hewlett Packard Enterprise Development LP.
#
# Unpublished Proprietary Information.
# This unpublished work is protected to trade secret, copyright and other laws.
# Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
# no part of this work or its content may be used, reproduced or disclosed
# in any form.
#

SRC					= @VALGRIND4HPC_DIR@/src

AM_CXXFLAGS			= -Wall -I$(SRC) -std=c++11
AM_LIBTOOLFLAGS		= --quiet

bin_PROGRAMS		= valgrind4hpc
libexec_PROGRAMS	= valgrind4hpc_daemon valgrind4hpc_starter
lib_LTLIBRARIES		= libvalgrind4hpc_filters.la

valgrind4hpc_SOURCES	= valgrind4hpc_FE.C
valgrind4hpc_CXXFLAGS	= @CRAY_CTI_FE_CFLAGS@ $(CRAY_MRNET_CFLAGS) $(CODE_COVERAGE_CXXFLAGS) $(AM_CXXFLAGS)
valgrind4hpc_LDFLAGS	= -Wl,--as-needed -Wl,-rpath,$(libdir) -lpthread $(AM_LDFLAGS)
valgrind4hpc_LDADD		= @CRAY_CTI_FE_LIBS@ $(CRAY_MRNET_LIBS) $(CODE_COVERAGE_LIBS)

valgrind4hpc_daemon_SOURCES		= valgrind4hpc_BE.C ValgrindOutput.C
valgrind4hpc_daemon_CXXFLAGS	= @CRAY_CTI_BE_CFLAGS@ $(CRAY_MRNET_CFLAGS) $(CODE_COVERAGE_CXXFLAGS) $(AM_CXXFLAGS)
valgrind4hpc_daemon_LDFLAGS		= -lpthread -Wl,--as-needed -Wl,-rpath,$(libdir) $(AM_LDFLAGS)
valgrind4hpc_daemon_LDADD		= @CRAY_CTI_BE_LIBS@ $(CRAY_MRNET_LIBS) $(CODE_COVERAGE_LIBS)

valgrind4hpc_starter_SOURCES	= valgrind4hpc_starter.C
valgrind4hpc_starter_CXXFLAGS	= $(CODE_COVERAGE_CXXFLAGS) $(AM_CXXFLAGS)
valgrind4hpc_starter_LDFLAGS	= -Wl,--as-needed -Wl,-rpath,$(libdir)  -lpthread $(CODE_COVERAGE_LDFLAGS) $(AM_LDFLAGS) -ldl

libvalgrind4hpc_filters_la_SOURCES	= valgrind4hpc_filters.C
libvalgrind4hpc_filters_la_CXXFLAGS	= $(CRAY_MRNET_CFLAGS) -fPIC $(CODE_COVERAGE_CXXFLAGS) $(AM_CXXFLAGS)
libvalgrind4hpc_filters_la_LDFLAGS	= -shared -avoid-version -Wl,--as-needed -Wl,-rpath,$(libdir) \
									 $(CODE_COVERAGE_LDFLAGS) $(AM_LDFLAGS)

#
# Makefile.am for the frontend components of the craytool interface.
#
# Copyright 2014-2019,2021 Hewlett Packard Enterprise Development LP.
#
# Unpublished Proprietary Information.
# This unpublished work is protected to trade secret, copyright and other laws.
# Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
# no part of this work or its content may be used, reproduced or disclosed
# in any form.
#

SRC             = @VALGRIND4HPC_DIR@/src
SUPPORT         = @VALGRIND4HPC_DIR@/tests/test_support

GTEST           = $(SUPPORT)/googletest/googletest
GMOCK           = $(SUPPORT)/googletest/googlemock

AM_CXXFLAGS     = -Wall -std=c++11
AM_LIBTOOLFLAGS = --quiet

TESTS = unit_tests
check_PROGRAMS = unit_tests

unit_tests_SOURCES  = unit_tests.cpp valgrind4hpc_aggregator_test.cpp MsgQueue_test.cpp TSQueue_test.cpp XmlChunker_test.cpp Socket_test.cpp ExecvpOutput_test.cpp
unit_tests_CFLAGS   = $(AM_CFLAGS) -fPIC -I$(SRC) \
	-I$(GTEST)/include -I$(GTEST)
unit_tests_CXXFLAGS = $(AM_CXXFLAGS) $(MRNET_CXXFLAGS) $(unit_tests_CFLAGS)
unit_tests_LDADD    = -ldl -lrt -lstdc++ $(MRNET_LIBS) \
	$(SUPPORT)/libgtest.la
unit_tests_LDFLAGS  = $(MRNET_LDFLAGS) \
	-pthread -Wl,-z,origin -Wl,-rpath,\$$ORIGIN -Wl,--enable-new-dtags \
	-Wl,--no-undefined -Wl,--as-needed

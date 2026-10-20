#
# Makefile.am for the Valgrind4hpc test support files
#
# Copyright 2014-2019,2020-2021 Hewlett Packard Enterprise Development LP.
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

AM_LIBTOOLFLAGS = --quiet
AUTOMAKE_OPTIONS = subdir-objects

# google test framework library
check_LTLIBRARIES   = libgtest.la
libgtest_la_SOURCES  = googletest/googletest/src/gtest-all.cc
libgtest_la_CPPFLAGS = -I$(GTEST)/include -I$(GTEST)
libgtest_la_LDFLAGS  = -pthread

# google mock framework library
check_LTLIBRARIES  += libgmock.la
libgmock_la_SOURCES  = googletest/googlemock/src/gmock-all.cc
libgmock_la_CPPFLAGS = -I$(GTEST)/include -I$(GTEST) \
	 -I$(GMOCK)/include -I$(GMOCK)
libgmock_la_LDFLAGS  = -pthread

#
# Makefile.am for automatic suppression generator components.
#
# Copyright 2017,2020-2021 Hewlett Packard Enterprise Development LP..
#
# Unpublished Proprietary Information.
# This unpublished work is protected to trade secret, copyright and other laws.
# Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
# no part of this work or its content may be used, reproduced or disclosed
# in any form.
#

SRC                 	= @VALGRIND4HPC_DIR@/suppressions

AM_CXXFLAGS       		= -Wall
AM_LIBTOOLFLAGS 		= --quiet

noinst_PROGRAMS			= supp_generator

supp_generator_SOURCES	= suppression_generator.C
supp_generator_CXXFLAGS	= $(AM_CXXFLAGS)

BUILT_SOURCES = libmpich_cray.supp libpmi.supp libfabric.supp misc.supp

%.supp: $(SRC)/in_files/%.in supp_generator
	$(SRC)/supp_generator -f $< -o $@

CLEANFILES = $(BUILT_SOURCES) supp_generator
suppdir = $(datadir)/suppressions
supp_DATA = $(BUILT_SOURCES) fixed_supp/known.supp fixed_supp/libcxi.supp

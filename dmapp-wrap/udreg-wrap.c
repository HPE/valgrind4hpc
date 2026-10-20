/******************************************************************************\
 * udreg-wrap.c - udreg wrappers for Valgrind Memcheck
 *
 * Copyright 2015-2018,2020 Hewlett Packard Enterprise Development LP.
 *
 * Unpublished Proprietary Information.
 * This unpublished work is protected to trade secret, copyright and other laws.
 * Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
 * no part of this work or its content may be used, reproduced or disclosed
 * in any form.
 *
 ******************************************************************************/

#include <stdio.h>
#include <unistd.h>

#include "memcheck-common.h"

#include <udreg_pub.h>

#define UDREG_WRAPPER(name) I_WRAP_SONAME_FNNAME_ZU(libudregZaZdsoZa,name)

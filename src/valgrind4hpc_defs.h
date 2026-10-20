/******************************************************************************\
 * valgrind4hpc_defs.h - Common definitions.
 *
 * Copyright 2015-2019,2020 Hewlett Packard Enterprise Development LP.
 *
 * Unpublished Proprietary Information.
 * This unpublished work is protected to trade secret, copyright and other laws.
 * Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
 * no part of this work or its content may be used, reproduced or disclosed
 * in any form.
 *
 ******************************************************************************/

#ifndef _VALGRID4HPC_DEFS_H
#define _VALGRID4HPC_DEFS_H

#define APG_LOCAL_HOST          NULL//"127.0.0.1" <--- used to be out home, but for loopback it should be NULL according to the man page.
#define APG_SOCK_FILE           "/tmp/valgrind4hpc_sock"
#define APG_BIN_FILE            "/tmp/valgrind4hpc_bin"

#define APG_STARTER             "valgrind4hpc_starter"
#define APG_BASE_DIR_ENV        "VALGRIND4HPC_INSTALL_DIR"
#define APG_VALGRIND_DIR_ENV    "VALGRIND4HPC_VALGRIND_DIR"
#define APG_IGNORE_SUPP_ENV     "VALGRIND4HPC_IGNORE_SUPPRESSIONS"

#endif /* _VALGRID4HPC_DEFS_H */

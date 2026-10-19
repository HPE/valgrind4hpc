# Copyright 2021-2023 Hewlett Packard Enterprise Development LP
#
# Environment variables

# when set to 1, logging will be more verbose
DEBUG = "CDST_TESTS_DEBUG"

# where log files will be created
LOG_DIR = "CDST_TESTS_LOG_DIR"

# directory containing the cdst_test library directory
LIB_DIR = "CDST_TESTS_LIB_DIR"

# connection passwords
#
# dcldap password used to initially connect to machines to install ssh keys.
# no CDST_TESTS_ prefix here since there is a semi-standard tool (sshpass) that
# reads this environment variable, and it is used as a fallback if expect isn't
# present on the client machine.
SSHPASS = "SSHPASS"
# username and password used to connect to shasta ncns
NCN_USER    = "CDST_TESTS_NCN_USER"
NCN_SSHPASS = "CDST_TESTS_NCN_SSHPASS"

# the below variables are intended for internal use and should not be set by a user.

# remote test tool startup variables
#
# if set, immediately chdir to specified path
CHDIR = "CDST_TESTS_CHDIR"
# prevents infinite recursion in job_environment.py's restart functions
DONT_RESTART_WRAPPED = "CDST_TESTS_DONT_RESTART_WRAPPED"
DONT_RESTART_SUBSHELL = "CDST_TESTS_DONT_RESTART_SUBSHELL"
# on some pals systems, allocating nodes sends you to a different machine. this
# variable is used to help the client track down the new machine.
UNALLOCED_HOSTNAME =  "CDST_TESTS_UNALLOCED_HOSTNAME"
# sometimes when you call /usr/bin/hostname on a remote machine, it will come
# back with a different name than what you connected to it with. to make database
# lookups consistent, we set this variable at connection time
WHEREAMI = "CDST_TESTS_WHEREAMI"

# internal logging variables
#
LOG_FILE_NAME = "CDST_TESTS_LOG_FILE_NAME"

# disable color printing if set
LOG_NO_COLOR = "CDST_TESTS_LOG_NO_COLOR"

# Root directory under which all testing happens. Set to cwd after server starts
# and read by some server opertions.
SERVER_ROOT = "CDST_TESTS_SERVER_ROOT"

# String set if test_tool_config contains a test/skips section. Each item in the
# test/skips section is put into this environment variable, separated by commas.
SKIPS = "CDST_TESTS_SKIPS"

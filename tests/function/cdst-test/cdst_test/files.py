# Copyright 2021 Hewlett Packard Enterprise Development LP
#
# Helper functions for retrieving files in this library

import os, shutil

# returns absolute path to base of the cdst_test library
def lib_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))

# return absolute path to data directory
def data() -> str:
    return lib_dir() + "/data"

# return absolute path to scripts directory
def scripts() -> str:
    return lib_dir() + "/scripts"

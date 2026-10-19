#!/usr/bin/env python3
#
# configure avocadco to our liking
#
# 1. set a custom log dir more local to this repo
# 2. set a sane value for parallel tasks

import os
import sys
import configparser

#sys.argv[1] contains path to avocado virtual env
#sys.argv[2] contains version of python used for install

#read in avocado configs
avocado_dir_path = os.path.abspath(sys.argv[1])
config = configparser.ConfigParser()
avocado_config_path = avocado_dir_path + "/avocado/lib/" + sys.argv[2] + "/site-packages/avocado/etc/avocado/avocado.conf"
print("Reading " + avocado_config_path)
config.read(avocado_config_path)

#customize configurations. See avocado.conf for configurables
print("Setting " + avocado_dir_path + "/job-results" + " as job results directory")

if "datadir.paths" not in config:
	config["datadir.paths"] = {}

config["datadir.paths"]["logs_dir"] = avocado_dir_path + "/job-results"

if "nrunner" not in config:
	config["nrunner"] = {}

config["nrunner"]["status_server_auto"] = "False"
config["nrunner"]["max_parallel_tasks"] = "4"

#write changes to config file
with open (avocado_config_path, 'w') as acp:
	config.write(acp)

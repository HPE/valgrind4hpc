# Copyright 2021 Hewlett Packard Enterprise Development LP
#
# Read and act upon the contents of a yaml file

import subprocess, sys, collections.abc, socket, os, re

import cdst_test.env as env
from . config_nodes import YamlRoot
from . config_default import get_default_config
from . import log

# To cache config loads
CONFIG_FILENAME = None
CONFIG = None

# some systems don't have yaml
try:
    import yaml
except ModuleNotFoundError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "--user"])
    import yaml

# "patch" a dict with another (the patch). If topatch has children that match
# patch, replace those contents with the contents of patch. Used when merging
# configs.
def patch_dict(topatch, patch):
    for k, v in patch.items():
        if isinstance(v, collections.abc.Mapping):
            # topatch.get(k, {}) will return an empty dict if nothing exists for
            # that key, but None is not nothing, and None is also bad, so we turn
            # that into an empty dict too
            next_topatch = topatch.get(k, {}) if topatch.get(k, {}) is not None else {}
            topatch[k] = patch_dict(next_topatch, v)
        else:
            topatch[k] = v

    return topatch

# read a .yaml file and generate a config tree from its contents
def load_config(filename) -> YamlRoot:
    global CONFIG, CONFIG_FILENAME

    if CONFIG is not None and CONFIG_FILENAME == filename:
        log.debug(f"Loading cached config ({filename})")
        return CONFIG

    log.debug("Reading config: " + filename)

    try:
        raw_config = yaml.safe_load(open(filename, "r").read())
    except FileNotFoundError as e:
        log.warn(f"Couldn't find test tool config file \"{filename}\". Using defaults.")
        raw_config = None

    # check for hostname-specific arguments
    hostname = socket.gethostname() if not os.getenv(env.WHEREAMI) else os.getenv(env.WHEREAMI)
    log.debug("Hostname: " + hostname)

    if raw_config and hostname in raw_config:
        # try plaintext matching
        log.info("Found %s in %s. Applying argument overrides" % (hostname, filename))
        raw_config = patch_dict(raw_config, raw_config[hostname])
    elif raw_config:
        log.debug("Looking for regex matches...")
        matched = False
        # try regex matching
        for node, tree in raw_config.items():
            if '*' in node:
                # create a regex
                r = re.compile(node.replace("*", ".*"))
                if r is None:
                    log.debug(f"Failed to turn {node} into a regex. Skipping.")
                    continue
                if r.match(hostname):
                    log.info(f"Matched \"{node}\" in {filename}, Applying argument overrides.")
                    raw_config = patch_dict(raw_config, tree)
                    matched = True
                    break
        if not matched:
            log.debug("No special hostname configuration found. Using defaults.")

    config = get_default_config()
    if raw_config:
        config.patch_from_dict(raw_config)

    CONFIG = config
    CONFIG_FILENAME = filename

    return config

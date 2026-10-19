# Copyright 2021-2023 Hewlett Packard Enterprise Development LP
#
# Contruct the default config from nodes in config_nodes

from . import config_nodes as nodes
from . import env

def get_default_config():
    root = nodes.YamlRoot()

    root.add_children([
        get_default_build_root(),
        get_default_test_root(),
        get_default_launch_root(),
        get_default_meta_root()
    ])

    return root

def get_default_build_root():
    build_root = nodes.Node("build", "apply at test build time")

    modules = nodes.LoadModules()
    setenv = nodes.SetEnvVars()
    prependenv = nodes.PrependEnvVars()
    presentenv = nodes.EnvVarsPresent()
    pkg = nodes.PkgConfig()
    target = nodes.MakeTarget()

    targets = nodes.NodeList("targets", nodes.MakeTarget, "build targets")
    targets.add_child(target)

    build_root.add_children([modules, prependenv, setenv, presentenv, pkg, targets])

    return build_root

def get_default_test_root():
    test_root = nodes.Node("test", "apply just before running tests")

    modules = nodes.LoadModules()
    env_vars = nodes.EnvVarsPresent()
    prep_env_vars = nodes.PrependEnvVars()
    path = nodes.KeyValue("path", ".", "path to directory with tests.py")
    parallel = nodes.KeyValue("parallel-jobs", 1, "number of tests to run at once")
    skips = nodes.List("skips", [], f"populate ${env.SKIPS}. see env.py")

    test_root.add_children([modules, env_vars, prep_env_vars, path, parallel, skips])

    return test_root

def get_default_launch_root():
    launch_root = nodes.Node("launch", "apply to all wlm invocations, including pre-test sanity checks")

    # default is 4 nodes
    alloc = nodes.Dict("allocation", {
        "slurm": "-N4 -t 3:00:00",
        "alps": "-l select=4:ncpus=4,place=scatter,walltime=3:00:00",
        "pals": "-l select=4:ncpus=4,place=scatter,walltime=3:00:00",
        "ssh": "",
        "always": False
    }, "if an explicit job allocation is required, allocate with these parameters")

    args = nodes.Dict("args", {
        "slurm": "", "alps": "", "pals": "", "ssh": "",
    }, "apply these launcher arguments to every job launch")

    mods = nodes.LoadModules()

    env = nodes.EnvVarsPresent()
    senv = nodes.SetEnvVars()
    prepenv = nodes.PrependEnvVars()

    launch_root.add_children([args, alloc, mods, env, senv, prepenv])

    return launch_root

def get_default_meta_root():
    meta_root = nodes.Node("meta", "options having to do with the test tool itself")

    version = nodes.KeyValue("avocado-version", "82.0", "version of avocado and avocado plugins to install")
    keep = nodes.List("keep", [], "don't delete these files upon -r option")

    meta_root.add_children([version, keep])

    return meta_root

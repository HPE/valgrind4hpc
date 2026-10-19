# Copyright 2021 Hewlett Packard Enterprise Development LP
#
# Functions to setup the environment such that jobs can be launched

import os, sys, socket, pty, subprocess, re

import cdst_test.config as config
import cdst_test.log as log
import cdst_test.modules as modules
import cdst_test.env as env

from cdst_test.useful import detect_wlm

# Detect if the current environment can run jobs as-is and take steps to fix it
# if it can't. Returns true if the environment can run jobs and false if not/on error
def setup_job(yaml_file) -> bool:
    log.info("Setting up job launch environment...")

    if os.getenv(env.CHDIR):
        dir = os.getenv(env.CHDIR)
        os.chdir(dir)
        log.debug(f"Changed directory to {dir}")

    cfg = config.load_config(yaml_file)

    # load any modules we need for launching
    if not cfg.apply("launch/modules"):
        # error message handled in cfg
        return False

    wlm = detect_wlm()

    if wlm == "SLURM" and detect_slurm_gres_bug() and not os.getenv("CTI_SLURM_DAEMON_GRES"):
        log.warn("Detected slurm 21.08.2, which has a known bug with --gres.")
        log.warn("See https://bugs.schedmd.com/show_bug.cgi?id=12642.")
        log.warn(f"Setting CTI_SLURM_DAEMON_GRES to \"\".")
        log.warn("If this environment variable is specified in test_tool_config.yaml, it will be overwritten by the value specified there.")
        os.environ["CTI_SLURM_DAEMON_GRES"] = ""

    # get a job allocation
    if (wlm == "ALPS" or wlm == "PALS") and not os.getenv("PBS_JOBCOOKIE"):
        log.warn("A job allocation is required under ALPS/PALS, restarting under an allocation...")
        os.environ[env.UNALLOCED_HOSTNAME] = socket.gethostname()
        nodelist_args = cfg.get("launch/allocation/alps") if wlm == "ALPS" else cfg.get("launch/allocation/pals")
        # exec's and starts over
        restart_wrapped(["qsub", "-VI", *nodelist_args.split(" "), "--"], fake_tty=True)
    if cfg.get("launch/allocation/always") and wlm == "SLURM" and not os.getenv("SLURM_JOB_ID"):
        log.warn("Restarting under an allocation...")
        os.environ[env.UNALLOCED_HOSTNAME] = socket.gethostname()
        alloc_args = str(cfg.get("launch/allocation/slurm"))
        restart_wrapped(["salloc", *alloc_args.split(" ")])

    return True

def detect_slurm_gres_bug():
    # "slurm xx.yy.z"
    slurm_vers_str = subprocess.run(["srun", "--version"], stdout=subprocess.PIPE).stdout.decode().rstrip()
    m = re.match(r'\D*(\d+)\.(\d+)\.(\d+)(-(\d))?.*', slurm_vers_str)
    if m:
        try:
            # "xx.yy.z" or "xx.yy.z-a"
            xx = int(m.group(1))
            yy = int(m.group(2))
            z  = int(m.group(3))
            a  = int(m.group(5)) if m.group(5) else 0
            slurm_vers = (1000**2 * xx) + (1000 * yy) + (10 * z) + a
            log.debug(f"Parsed slurm version: {slurm_vers_str} -> {slurm_vers}")
        except Exception as e:
            log.warn(f"Could not parse slurm version: {slurm_vers_str} ({str(e)})")
            slurm_vers = 0
    else:
        log.warn(f"Could not parse slurm version: {slurm_vers_str}")
        slurm_vers = 0

    # bug introduced in 21.08.0, fixed in 21.08.5
    return 21008000 <= slurm_vers < 21008050

# Detect if the current environment can build mpi apps and take steps to fix
# it if it can't. Returns true if the environment can build an mpi app.
def setup_mpi_build() -> bool:
    log.info("Setting up build environment...")

    # on some systems, source $CRAY_ENABLE_PE is required to set up the environment.
    if os.getenv("CRAY_ENABLE_PE") and (not modules.list("craype")):
        log.warn("Detected $CRAY_ENABLE_PE, but the craype module isn't loaded.")
        log.warn("Trying to source $CRAY_ENABLE_PE and restart...")
        # exec's and starts over
        restart_wrapped_subshell("source $CRAY_ENABLE_PE")

    return True

# restart the test tool wrapped in the passed wrapper binary.
#
# e.g. restart_wrapped(["qsub", "...", "..."])
def restart_wrapped(wrapper : list, fake_tty: bool = False):
    if os.getenv(env.DONT_RESTART_WRAPPED):
        log.error(f"{env.DONT_RESTART_WRAPPED} prevented restart.")
        exit(-1)

    me = os.getcwd() + "/" + sys.argv[0]
    argv = wrapper + [me] + sys.argv[1:]

    # change working directory on startup, needed when allocating jobs under PALS
    os.environ[env.CHDIR] = os.getcwd()
    # don't try to restart again, avoiding infinite recursion
    os.environ[env.DONT_RESTART_WRAPPED] = "1"

    log.warn(f"Running {argv}")
    if not fake_tty:
        os.execvp(argv[0], argv)
    else:
        exit(pty.spawn(argv))

# restart the test tool after running the wrapper command in a subshell.
#
# e.g. restart_wrapped_subshell("source $CRAY_ENABLE_PE")
def restart_wrapped_subshell(wrapper : str):
    if os.getenv(env.DONT_RESTART_SUBSHELL):
        log.error(f"{env.DONT_RESTART_SUBSHELL} prevented restart.")
        exit(-1)

    current_argv_str = " ".join(sys.argv)
    argv = ["/bin/bash", "-c", wrapper + "; " + current_argv_str]

    # don't try to restart again, avoiding infinite recursion
    os.environ[env.DONT_RESTART_SUBSHELL] = "1"

    log.warn(f"Running {argv}")
    os.execvp(argv[0], argv)

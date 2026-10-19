# Copyright 2020-2021 Hewlett Packard Enterprise Development LP
#
# Cross platform interface to the module command

import os, sys
import subprocess
from . import log

# import python module function
try:
    MODULES_HOME = os.environ['MODULESHOME']
except KeyError as e:
    log.warn("Couldn't read %s from environment. Are modules available? Local python module functionality won't work." % e)
    MODULES_HOME = None

if MODULES_HOME is not None:
    sys.path.insert(0, MODULES_HOME + "/init/")

# detect if we are tmod or lmod (tcl or lua modules)
def detect_modules_flavor() -> str:
    version_p = subprocess.run("module --version", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    version_output = (version_p.stdout.decode() + "\n" + version_p.stderr.decode()).strip()
    # tmod begins its version output with "VERSION=" or "Modules Release"
    if version_output.startswith("VERSION=") or version_output.startswith("Modules Release"):
        return "tmod"
    elif version_output.startswith("Modules based on Lua:"):
        return "lmod"
    else:
        log.error("Couldn't detect modules flavor. Output of module --version was:")
        log.info(version_output)
        return None

if MODULES_HOME:
    MODULES_FLAVOR = detect_modules_flavor()
else:
    MODULES_FLAVOR = None

log.debug(f"Set flavor to {MODULES_FLAVOR}")

try:
    if MODULES_FLAVOR == "tmod":
        from python import module
    elif MODULES_FLAVOR == "lmod":
        from env_modules_python import module
    else:
        # can get here if running on a system without modules
        log.warn("Couldn't detect modules flavor (expected on systems without modules available)")
except (ModuleNotFoundError, ImportError, SyntaxError) as e:
    log.warn(f"Couldn't import python modules library ({e}). Module functions will not work.")

if MODULES_HOME and MODULES_FLAVOR:
    # on some versions of environment modules, the shell command does not have a meaningful exit code
    MODULE_SHELL_RETURNCODE_RELIABLE = subprocess.run("module testing...", shell=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0
else:
    MODULE_SHELL_RETURNCODE_RELIABLE = False

log.debug("Module shell return code is%s reliable." %
    (" not" if not MODULE_SHELL_RETURNCODE_RELIABLE else ""))

# test if a module command will be successful.
# note: this runs the command in a subshell, so the effects of whatever command
# is run *won't* be applied. use invoke_successfully for that.
# this exists as a silent way to check if a call will be successful.
def dry_run(*args) -> bool:
    log.debug("dry_run: %s" % " ".join(args))
    p = subprocess.run("module " + " ".join(args), shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if MODULE_SHELL_RETURNCODE_RELIABLE:
        if p.returncode != 0:
            log.error((p.stdout + p.stderr).decode())
            return False
        else:
            return True

    # return code isn't reliable, time to get hacky...
    error_strings = []
    if MODULES_FLAVOR == "tmod":
        error_strings += [
            "Invalid command",
            "ERROR:"
        ]
    elif MODULES_FLAVOR == "lmod":
        error_strings += [
            "Modules based on Lua: Version", # emitted on an invalid command
            "Lmod has detected the following error:"
        ]

    output = (p.stdout + p.stderr).decode()

    for estr in error_strings:
        if estr in output:
            log.debug(f"found {estr} in output.")
            log.error((p.stdout + p.stderr).decode())
            return False

    log.debug("detected nothing wrong!")
    return True

# return a list of available module files. if grep is specified, filter
# the results to match it. returns None on error.
def avail(grep : str = "") -> list:
    log.debug(f"avail ({grep})")

    if not dry_run("-t", "avail", grep):
        return None

    output = capture_output("-t", "avail", grep)

    avail = []

    for line in output.splitlines():
        # filter out "(default)"
        line = line.replace("(default)", "")

        # filter out locations e.g. "opt/modulefiles:"
        if line[-1:] == ':':
            continue

        if grep != "" and grep in line:
            avail.append(line)
        elif grep == "":
            avail.append(line)

    log.debug(f"avail ({grep}) {avail}")
    return avail

# return a list of currently loaded module files. if grep is specified, filter
# the results to match it. returns None on error.
def list(grep : str = "") -> list:
    log.debug(f"list ({grep})")

    if not dry_run("-t", "list"):
        return None

    output = capture_output("-t", "list")
    list = []
    lines = []

    if MODULES_FLAVOR == "tmod":
        lines = output.splitlines()[1:]
    elif MODULES_FLAVOR == "lmod":
        lines = output.splitlines()
    else:
        # should never get here
        raise RuntimeError()

    for line in lines:
        if grep != "" and grep in line:
            list.append(line)
        elif grep == "":
            list.append(line)

    log.debug(f"list ({grep}) -> {list}")
    return list

# return the install location of a given module
def find_install_location(module : str) -> str:
    log.debug(f"find_install_location: {module}")
    show_output = capture_output("show", module)
    version_line = show_output.splitlines()[1]
    version = None

    if MODULES_FLAVOR == "tmod":
        version = version_line[version_line.rfind("/") + 1:-1] # remove ":"
    elif MODULES_FLAVOR == "lmod":
        version = version_line[version_line.rfind("/") + 1:-5] # remove ".lua:"
    else:
        # should never get here
        raise RuntimeError()

    log.debug(f"detected \"{version}\"")

    for line in show_output.splitlines():
        # try to find a path pointing to the install directory
        # for tmod:
        #   e.g. setenv CTI_INSTALL_DIR /opt/cray/pe/.../<version/...
        #   e.g. prepend_path PATH /opt/cray/pe/.../<version>/...
        # for lmod:
        #   e.g. setenv("CTI_INSTALL_DIR","/opt/cray/pe/.../<version>/...")
        #   e.g. prepend_path("PATH","/opt/cray/pe/.../<version>/...")
        if len(line) >= 6 and line[:6] == "setenv" and "_INSTALL_DIR" in line and version in line \
        or len(line) >= 12 and line[8:12] == "path" and "PATH" in line and version in line:
            return line[line.find('/'):line.rfind(version) + len(version)]
    return None

# run a module command and return if it was successful or not
def invoke_successfully(*args) -> bool:
    log.debug("invoke_successfully: %s" % " ".join(args))
    if not dry_run(*args):
        return False
    module(*args)
    return True

# capture the output of a module command.
# note: this runs the command in a subshell, so the effects of whatever command
# is run *won't* be applied. use invoke_successfully for that.
def capture_output(*args) -> str:
    log.debug("capture_output: %s" % " ".join(args))
    p = subprocess.run("module " + " ".join(args), shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    log.debug(f"output:\n{p.stdout.decode() + p.stderr.decode()}")
    return p.stdout.decode() + p.stderr.decode()

#!/usr/bin/env python3

import argparse
import os, sys
import shutil
import subprocess
import itertools
import pathlib
import threading
import functools
import socket
import random

from cdst_test.useful import detect_wlm, successful_launch
import cdst_test.log as log
import cdst_test.modules as modules
import cdst_test.config as config
import cdst_test.files as files
import cdst_test.env as env
import cdst_test.job_environment as jenv
import cdst_test.bootstrap as boot

def parse_arguments():
    parser = argparse.ArgumentParser(description="Run functional tests")

    parser.add_argument("-t", "--test", help="run a single test. if this option isn't used, all tests are run. can be used multiple times to run multiple tests.", metavar="TEST", action="append")
    parser.add_argument("-s", "--skip-build", help="skip the build step.", action="store_true")
    parser.add_argument("-f", "--force", help="force tests to run, even if a check fails.", action="store_true")
    parser.add_argument("-r", "--remove", "--clean", help="remove local files that get created when this tool is run.", action="store_true")
    parser.add_argument("-y", "--yaml", help="specify a yaml file with extra config. default is test_tool_config.yaml.", metavar="FILE")
    parser.add_argument("-c", "--config", help="specify an avocado yaml file for use with --mux-yaml. default is avocado_config.yaml.", metavar="CONFIG")
    parser.add_argument("-e", "--env", help="dump environment info and exit.", action="store_true")
    parser.add_argument("-m", "--mux-filter-only", help="pass to avocado's --mux-filter-only argument.", metavar="FILTER")
    parser.add_argument("-p", "--print-config", help="print configuration after reading the specified config file and applying hostname overrides, then exit.", action="store_true")
    parser.add_argument("-d", "--print-default-config", help="print a default test_tool_config.yaml file and exit.", action="store_true")
    parser.add_argument("-k", "--skip-precheck", help="skip the precheck step.", action="store_true")

    return parser.parse_args()

def copy_to(location):
    log.info("Copying tests to " + location)

    if os.path.exists(location):
        log.error("Couldn't copy. %s exists." % location)
        return False

    shutil.copytree(".", location)
    log.info("Now cd %s and run the test tool." % location)

def build_tests(yaml_file):
    cfg = config.load_config(yaml_file)

    log.info("Running prebuild checks...")

    log.debug("prebuild check: modules")
    if not cfg.apply("build/modules"):
        # error message handled in cfg
        return False

    log.debug("prebuild check: environment")
    if not cfg.apply("build/environment"):
        # error message handled in cfg
        return False

    log.debug("prebuild check: prepend-env-vars")
    if not cfg.apply("build/prepend-env-vars"):
        # error message handled in cfg
        return False

    log.debug("prebuild check: env-vars-present")
    if not cfg.apply("build/env-vars-present"):
        # error message handled in cfg
        return False

    log.debug("prebuild check: pkg-config")
    if not cfg.apply("build/pkg-config"):
        # error message handled in cfg
        return False

    log.info("Building tests...")

    if os.path.exists("configure.ac"):
        if not successful_launch(["autoreconf", "-ifv"]):
            log.error("autoreconf failed.")
            return False

        if not successful_launch(["./configure"]):
            log.error("./configure failed.")
            return False

    # Apply WLM environment setting for test build
    os.environ["CDST_TESTS_WLM"] = detect_wlm()

    if not cfg.apply("build/targets"):
        # error message emitted in cfg
        return False

    return True

def clean(yaml_file):
    log.info("Cleaning up test environment")

    cfg = config.load_config(yaml_file)
    tests_path = cfg.get("test/path")

    subprocess.run(["make", "clean"])

    files = [
        "avocado",
        "hello_mpi.c",
        "hello_mpi",
        "aclocal.m4",
        "ar-lib",
        "compile",
        "config.guess",
        "config.log",
        "config.status",
        "config.sub",
        "configure",
        "depcomp",
        "install-sh",
        "libtool",
        "ltmain.sh",
        "Makefile.in",
        "missing",
        "./m4/libtool.m4",
        "./m4/lt~obsolete.m4",
        "./m4/ltoptions.m4",
        "./m4/ltsugar.m4",
        "./m4/ltversion.m4"
    ]

    dirs = [
        "autom4te.cache",
        tests_path + "/avocado-virtual-environment",
        "__pycache__"
    ]

    # keep any files specified in the yaml file under /meta/keep
    keeplist = cfg.get("meta/keep")

    for keep in keeplist:
        log.warn(f"Note: keeping \"{keep}\" (specified in {yaml_file})")
        if keep in files:
            files.remove(keep)
        if keep in dirs:
            dirs.remove(keep)

    for f in files:
        try:
            os.remove(f)
        except FileNotFoundError:
            # file is already gone, that's fine
            pass

    for d in dirs:
        try:
            shutil.rmtree(d)
        except FileNotFoundError:
            # directory is already gone, that's fine
            pass

    return True

PASSED_SANITY_CHECKS = False

def sanity_checks(yaml_file):
    global PASSED_SANITY_CHECKS

    if PASSED_SANITY_CHECKS:
        return True
 
    cfg = config.load_config(yaml_file)
    log.debug("config: \n" + cfg.generate_yaml())

    # get custom path if it exists
    tests_path = cfg.get("test/path")

    # make sure we're in a writable directory
    if not os.access(".", os.W_OK):
        log.error("Current directory isn't writable.")
        log.info("Run $ cp -r . <destination> to move the tests into a writable directory.")
        return False

    wlm = None
    if "CDST_TESTS_LAUNCHER" not in os.environ:
        # detect launcher
        wlm = detect_wlm()
        if wlm == "SLURM":
            os.environ["CDST_TESTS_LAUNCHER"] = "srun"
        elif wlm == "ALPS" or wlm == "PALS":
            os.environ["CDST_TESTS_LAUNCHER"] = "aprun"
        elif wlm == "SSH":
            os.environ["CDST_TESTS_LAUNCHER"] = "mpiexec"
        elif wlm == "LOCALHOST":
            os.environ["CDST_TESTS_LAUNCHER"] = "localhost"
        elif wlm == "FLUX":
            os.environ["CDST_TESTS_LAUNCHER"] = "flux"
        else:
            if wlm:
                log.error("Couldn't detect a launcher for wlm: " + wlm)
            else:
                log.error("Couldn't detect a wlm. Is the module loaded?")

            return False
    else:
        log.warn("Using CDST_TESTS_LAUNCHER already in environment.")
        wlm = os.environ["CDST_TESTS_LAUNCHER"]

    log.debug("Detected " + os.environ["CDST_TESTS_LAUNCHER"])

    if "CDST_TESTS_LAUNCHER_ARGS" not in os.environ:
        if cfg.get(f"launch/args/{wlm.lower()}") != None:
            os.environ["CDST_TESTS_LAUNCHER_ARGS"] = cfg.get(f"launch/args/{wlm.lower()}")
        else:
            log.error("Didn't find configured launcher arguments in %s for %s." % (yaml_file, wlm.lower()))
            return False
    else:
        args = os.getenv("CDST_TESTS_LAUNCHER_ARGS")
        log.warn(f"Using CDST_TESTS_LAUNCHER_ARGS already in environment: \"{args}\"")

    log.info("Trying to run a basic mpi job...")
    log.debug("Using launcher arguments: " + os.environ["CDST_TESTS_LAUNCHER_ARGS"])

    # make sure we have launcher and launcher args
    required_vars = [
        "CDST_TESTS_LAUNCHER",
        "CDST_TESTS_LAUNCHER_ARGS"
    ]

    for v in required_vars:
        if v not in os.environ:
            log.error("Didn't find %s in the environment." % v)
            return False

    # set up environment
    if not cfg.apply("launch/environment"):
        # error emitted in apply
        return False

    if not cfg.apply("launch/prepend-env-vars"):
        # error emitted in apply
        return False

    if not cfg.apply("launch/env-vars-present"):
        # error emitted in apply
        return False

    # at this point we short-circuit if we already know we have already done setup in the past
    if os.path.exists(tests_path + "/avocado-virtual-environment/sane"):
        log.warn("Job launch sanity checks bypassed by presence of /avocado-virtual-environment/sane")
        PASSED_SANITY_CHECKS = True
        return True

    launcher = os.environ["CDST_TESTS_LAUNCHER"]
    if launcher == "localhost":
        launcher_list = []
    elif launcher == "flux":
        launcher_list = ["flux", "run"]
    else:
        launcher_list = [launcher]
        
    # try to run a simple job
    if launcher and not successful_launch([*launcher_list, *os.environ['CDST_TESTS_LAUNCHER_ARGS'].split(), "/usr/bin/hostname"]):
        log.error("Can't run a basic job. Do you have enough nodes allocated?")
        return False

    # get mpi app source from library
    shutil.copyfile(os.path.dirname(os.path.abspath(__file__)) + "/cdst_test/src/hello_mpi.c", "./hello_mpi.c")


    # try to build an mpi app
    if launcher and not successful_launch(["make", "-f", os.path.dirname(os.path.abspath(__file__)) + "/cdst_test/src/Makefile"]):
        log.error("Failed to build an mpi app.")
        return False

    # try to run an mpi app
    if launcher and not successful_launch([*launcher_list, *os.environ["CDST_TESTS_LAUNCHER_ARGS"].split(), "./hello_mpi"]):
        log.error("Can't run a basic mpi app. Do you need different launcher arguments?")
        log.info("Specify launcher_args in %s to change them." % yaml_file)
        return False

    log.info("Installing avocado in " + tests_path)

    # install avocado
    if not os.path.exists(tests_path + "/avocado-virtual-environment"):
        log.info("Creating avocado virtual environment...")
        # create env
        os.mkdir(tests_path + "/avocado-virtual-environment")
        if not successful_launch(["python3", "-m", "venv", tests_path + "/avocado-virtual-environment/avocado"], quiet=True):
            log.error("Failed to create avocado virtual environment.")
            return False

        log.info("Upgrading pip...")
        if not successful_launch([tests_path + "/avocado-virtual-environment/avocado/bin/pip3", "install", "--upgrade", "pip"], quiet=True):
            log.error("Failed to upgrade pip")
            return False

        log.info("Installing required libraries to virtual environment...")
        if not successful_launch([tests_path + "/avocado-virtual-environment/avocado/bin/pip3", "install", "-r", f"{os.path.dirname(os.path.abspath(__file__))}/cdst_test/requirements.txt"], quiet=True):
            log.error("Failled to install required libraries")
            return False

        avocado_version_str = "==" + cfg.get("meta/avocado-version")

        log.info(f"Installing avocado... ({avocado_version_str[2:]})")

        if avocado_version_str == "==latest":
            avocado_version_str = ""

        # install avocado
        if not successful_launch([tests_path + "/avocado-virtual-environment/avocado/bin/pip3", "install", f"avocado-framework{avocado_version_str}"], quiet=True):
            log.error("Failed to install avocado")
            return False

        # install plugins
        log.info("Installing avocado plugins...")
        plugins = [
            f"avocado-framework-plugin-varianter-yaml-to-mux{avocado_version_str}",
            f"avocado-framework-plugin-result-html{avocado_version_str}"
        ]

        for plug in plugins:
            log.info(f"Installing {plug}...")
            if not successful_launch([tests_path + "/avocado-virtual-environment/avocado/bin/pip3", "install", plug], quiet=True):
                log.error("Failed to install " + plug)
                return False

        # configure avocado
        log.info("Configuring avocado...")
        os.mkdir(tests_path + "/avocado-virtual-environment/job-results")
        pyversion = subprocess.check_output(["ls", tests_path + "/avocado-virtual-environment/avocado/lib"]).decode().rstrip()
        if not successful_launch([tests_path + "/avocado-virtual-environment/avocado/bin/python3", files.scripts() + "/avo_config.py", tests_path + "/avocado-virtual-environment", pyversion], quiet=True):
            log.error("Failed to configure avocado")
            return False

        # create a convenient symlink to the avocado binary
        log.info("Creating avocado symlink...")
        try:
            os.symlink(tests_path + "/avocado-virtual-environment/avocado/bin/avocado", "avocado")
        except FileExistsError:
            # silently continue
            log.debug("avocado symlink already exists?")

    log.info(f"Avocado installed in {tests_path}")

    # make sure tests.py exists
    if not os.path.exists(tests_path + "/tests.py"):
        log.error("Couldn't find %s/tests.py." % tests_path)
        return False

    # mark environment as sane
    pathlib.Path(tests_path + '/avocado-virtual-environment/sane').touch()

    PASSED_SANITY_CHECKS = True
    return True

def dump_environment_info():
    log.info("--- Environment Info ---")
    log.info(f"WLM: {detect_wlm()}")

    # lmod requires "-t" to come before "list"
    txt = modules.capture_output("-t", "list")

    # if found loaded, "module show <product>" will be called on these
    interesting_products = [
        "gdb4hpc",
        "valgrind4hpc",
        "atp",
        "cray-cti",
        "cray-cdst-support",
        "cray-zmqnet",
    ]

    # if a product in the above list is found, we will look for these postfixes
    # on the end
    interesting_postfixes = [
        "",
        "-tests",
        "-devel"
    ]

    seen = set()
    log.info("Cray CDST product install locations:")
    for line in txt.splitlines():
        for product in itertools.product(interesting_products, interesting_postfixes):
            fullname = product[0] + product[1]
            if fullname in line and fullname not in seen:
                location = modules.find_install_location(line)
                location = location if location else "?"
                log.info(f"{line}: {location}")
                seen.add(fullname)

    log.debug("System info:")
    log.debug(subprocess.check_output(["uname", "-a"])[:-1].decode())
    log.debug("Time and date:")
    log.debug(subprocess.check_output(["date"])[:-1].decode())

def run_test(yaml_file, avocado_config, t = None, mux_filter_only = None, threaded = False):
    # install prereqs
    if not boot.bootstrap():
        log.error("Failed to bootstrap.")
        return False

    if not sanity_checks(yaml_file):
        log.error("Failed common sanity checks")
        return False

    log.info("Passed sanity checks.")

    cfg = config.load_config(yaml_file)

    tests_path = cfg.get("test/path")

    log.info("Running pretest checks...")

    # load any modules we need for testing
    log.debug("modules")
    if not cfg.apply("test/modules"):
        # error message handled in cfg
        return False

    log.debug("env-vars-present")
    if not cfg.apply("test/env-vars-present"):
        # error message handled in cfg
        return False

    log.debug("prepend-env-vars")
    if not cfg.apply("test/prepend-env-vars"):
        # error message handled in cfg
        return False

    log.debug(f"building {env.SKIPS}")
    if len(cfg.get("test/skips")) > 0:
        skips = cfg.get("test/skips")
        stringified = ",".join(skips)
        os.environ[env.SKIPS] = stringified
        log.warn(f"Set ${env.SKIPS} to \"{stringified}\"")

    # generate port for test server
    port = str(random.randint(8888, 12222))
    single_test = ":" + str(t) if t is not None else ""

    launch = [
        "avocado-virtual-environment/avocado/bin/avocado", "run", "tests.py" + single_test,
        "--mux-yaml", avocado_config,
        "--status-server-disable-auto",
        "--status-server-listen", f"127.0.0.1:{port}",
        "--status-server-uri", f"127.0.0.1:{port}"
    ]

    pjobs = str(cfg.get("test/parallel-jobs"))
    log.warn(f"Setting max parallel jobs to {pjobs}")
    launch += ["--max-parallel-tasks", pjobs]

    if mux_filter_only is not None:
        log.debug(f"--mux-filter-only = {mux_filter_only}")
        launch += ["--mux-filter-only", mux_filter_only]

    dump_environment_info()
    log.info("Running " + " ".join(launch))

    if not threaded:
        return subprocess.run(launch, cwd=tests_path).returncode == 0
    else:
        go = functools.partial(subprocess.run, launch, cwd=tests_path)
        return threading.Thread(target=go, args=())

def run_tests():
    args = parse_arguments()

    if os.getenv(env.CHDIR):
        os.chdir(os.getenv(env.CHDIR))
        log.info(f"Changed cwd to {os.getcwd()}")

    yaml_file = "./test_tool_config.yaml"
    if args.yaml:
        yaml_file = args.yaml

    avo_config = "./avocado_config.yaml"
    if args.config:
        avo_config = args.config

    test_everything = True
    ignore_errors = False

    if args.env:
        dump_environment_info()
        return True

    if args.print_default_config:
        print(config.get_default_config().generate_yaml())
        return True

    if args.print_config:
        print(config.load_config(yaml_file).generate_yaml())
        return True

    if args.force:
        ignore_errors = True

    if args.remove:
        clean(yaml_file)
        test_everything = False
        args.skip_build = True

    if not args.skip_build:
        if not jenv.setup_mpi_build():
            log.error("Failed to setup mpi build environment")
            return False

        r = build_tests(yaml_file)
        if not r and not ignore_errors:
            log.error("Failed to build tests.")
            return False

    if not jenv.setup_job(yaml_file):
        log.error("Failed to setup environment for job launches")
        return False

    if args.test:
        for t in args.test:
            run_test(yaml_file, avo_config, t, mux_filter_only = args.mux_filter_only)
    elif test_everything:
        run_test(yaml_file, avo_config, mux_filter_only = args.mux_filter_only)

if __name__ == "__main__":
    exit(0 if run_tests() else -1)

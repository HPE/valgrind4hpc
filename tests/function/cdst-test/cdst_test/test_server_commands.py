# Copyright 2021-2023 Hewlett Packard Enterprise Development LP
#
# Responses to commands sent by the test client

# (public) functions in this file should follow the format:
# do_command(Command) -> Command

import os, time, shutil, fcntl, sys, pty, socket

import test_tool

import cdst_test.log as log
import cdst_test.modules as modules
import cdst_test.ssh as ssh
import cdst_test.artifactory as arti
import cdst_test.env as env
import cdst_test.job_environment as jenv
import cdst_test.useful as useful
import cdst_test.config as config

from cdst_test.test_server_proto import Command, Command as C, CommandType as CT
from cdst_test.useful import successful_launch

def do_setup_env(yaml: str, comm : Command, sock, conn) -> Command:
    # "setup env" is a catch-all term for "do whatever it takes to get from a blank login
    # shell to a state where we can launch an MPI job in an allocation".
    #
    # this process ends in restarting the test tool server under an allocation command.
    # this breaks the connection to the frontend, and the frontend immediately tries to reconnect.
    #
    # machines vary a lot in what needs to be done. some machines need to source a bash
    # script and then restart. all machines need to eventually restart under the job allocation command.
    # this means that in theory some machines need to run multiple restarts to setup. we want to only
    # restart once though, since the frontend only expects to have to reconnect once. the
    # most flexible way to do this is to write our own bash script and then execute it.
    # it's weird, but it works...

    setup_script_path = log.get_log_dir() + "/setup_launch_environment.sh"
    log.info(f"Writing setup script to {setup_script_path}")

    if yaml is None:
        return C(CT.ERROR, "Tried to setup job environment without config file")

    cfg = config.load_config(yaml)

    wlm = useful.detect_wlm()
    log.debug(f"WLM detected as \"{wlm}\"")

    # write our restart script
    with open(setup_script_path, "w") as script:
        script.write("#!/bin/bash\n\n")

        # on some systems, source $CRAY_ENABLE_PE is required to set up the environment.
        if os.getenv("CRAY_ENABLE_PE") and (not modules.list("craype")):
            script.write("# detected $CRAY_ENABLE_PE, but the craype module isn't loaded.\n")
            script.write("source $CRAY_ENABLE_PE\n\n")

        # ensure --gres bug in slurm 21.08.0 - 21.08.5 is accounted for
        if wlm == "SLURM" and not os.getenv("CTI_SLURM_DAEMON_GRES"):
            patch = """slurm_version=$(srun --version) # "slurm xx.yy.z-b"
slurm_version_slice=${slurm_version:0:11} # "slurm xx.yy"
if [[ $slurm_version_slice == "slurm 21.08" ]]
then
    # Detected slurm 21.08.x, which has a known bug with --gres.
    # See https://bugs.schedmd.com/show_bug.cgi?id=12642.
    export CTI_SLURM_DAEMON_GRES=""
fi

"""
            script.write(patch)

        # write final step to restart test server under a job allocation
        me = os.getcwd() + "/" + sys.argv[0]
        argv = [me] + sys.argv[1:]

        if wlm == "ALPS" and not os.getenv("PBS_JOBCOOKIE"):
            alloc_args = cfg.get("launch/allocation/alps")
            script.write(f'qsub -VI {alloc_args} -- {" ".join(argv)}\n')
        elif wlm == "PALS" and not os.getenv("PBS_JOBCOOKIE"):
            alloc_args = cfg.get("launch/allocation/pals")
            script.write(f'qsub -VI {alloc_args} -- {" ".join(argv)}\n')
        elif wlm == "SLURM" and not os.getenv("SLURM_JOB_ID"):
            alloc_args = cfg.get("launch/allocation/slurm")
            script.write(f'salloc {alloc_args} {" ".join(argv)}\n')
        else:
            log.error("Unknown WLM!")
            return C(CT.ERROR, "Unknown WLM")

    os.chmod(setup_script_path, 0o755)

    # if the job allocation command puts us on another node than we are now, the test
    # tool will read this environment variable and use an ssh tunnel to tell the frontend
    # where to go
    os.environ[env.UNALLOCED_HOSTNAME] = socket.gethostname()

    # prevent other restarts
    os.environ[env.DONT_RESTART_WRAPPED] = "1"
    os.environ[env.DONT_RESTART_SUBSHELL] = "1"

    # 3, 2, 1...
    log.warn(f"Restarting via {setup_script_path}!")

    resp = C(CT.TASK_FINISHED, "Restarting now").encode()
    conn.sendall(resp)

    # close connection so new process can bind on same port
    conn.close()
    sock.shutdown(socket.SHUT_RD)
    sock.close()

    # ...go! execute the script.
    if wlm == "ALPS" or wlm == "PALS":
        # use a pty because we passed -I to qsub
        exit(pty.spawn([setup_script_path]))
    else:
        # XXX some machines require the script be executed with bash -c source
        os.execvp("/bin/bash", ["/bin/bash", "-c", "source " + setup_script_path])

    return C(CT.ERROR, "unreachable")

def do_sanity_checks(yaml: dict, comm : Command) -> Command:
    r = test_tool.sanity_checks(yaml)
    if not r:
        return C(CT.ERROR, "Failed sanity checks")
    return C(CT.TASK_FINISHED, str(r))

def do_build(yaml: dict, comm : Command) -> Command:
    r = test_tool.build_tests(yaml)
    if not r:
        return C(CT.ERROR, "Failed build")
    return C(CT.TASK_FINISHED, str(r))

def do_tests(yaml: dict, comm : Command) -> Command:
    # Wait for a file to exist, return True when it does or False on timeout
    def wait_for_file(path : str) -> bool:
        basename = os.path.basename(path)
        attempt = 1
        max_attempts = 45
        while not os.path.isfile(path):
            log.info(f"Waiting for {basename}... ({attempt}/{max_attempts})")
            log.debug(f"Waiting for {path}... ({attempt}/{max_attempts})")
            attempt += 1
            if attempt > max_attempts:
                return False
            time.sleep(1)
        return True

    avo_conf = "./avocado_config.yaml"
    if len(comm.data) > 0:
        avo_conf = comm.data.rstrip()
    else:
        log.warn(f"Using defaul config {avo_conf}")

    log.info(f"Running tests ({yaml}, {avo_conf})")
    thr = test_tool.run_test(yaml, avo_conf, threaded=True)

    if isinstance(thr, bool) and thr == False:
        return C(CT.ERROR, "Failed to run tests")
    else:
        tapfile = "./avocado-virtual-environment/job-results/latest/results.tap"

        if os.path.isfile(tapfile):
            log.debug("Moving {tapfile}")
            os.rename(
                tapfile,
                tapfile + ".old"
            )

        # turns out that every test is run as a subprocess and would blow
        # away its log if we didn't open in append mode...
        os.environ["CDST_TESTS_LOG_FILE_NAME"] = "tests.log"
        if os.getenv("CDST_TESTS_LOG_DIR"):
            path = os.getenv("CDST_TESTS_LOG_DIR") + "/" + os.getenv("CDST_TESTS_LOG_FILE_NAME")
            if os.path.isfile(path):
                os.unlink(path)
        thr.start()

        # wait for results.tap to exist
        if not wait_for_file(tapfile):
            log.error(f"Never found {tapfile}")
            thr.join()
            return C(CT.ERROR, f"Never found {tapfile}")
        else:
            log.info("Waiting for first test result...")
            # stream results.tap to client
            tap = open(tapfile, "r")

            def stream_lines():
                line = tap.readline()
                while line != "":
                    # log hook set by layer above will stream this to client
                    log.info(line.rstrip())
                    line = tap.readline()

            while thr.is_alive():
                stream_lines()
                time.sleep(.3)
            # make sure we get the last lines
            stream_lines()

            r = thr.join()
            return C(CT.TASK_FINISHED, str(r))

def do_clean(yaml : dict, comm : Command) -> Command:
    return C(CT.TASK_FINISHED, str(test_tool.clean(yaml)))

def do_test_arti_connection(yaml: dict, comm: Command) -> Command:
    return C(CT.TASK_FINISHED, str(arti.test_artifactory_visibility()))

def do_get_arti_os(yaml: dict, comm: Command) -> Command:
    return C(CT.TASK_FINISHED, str(arti.detect_os_arti_folder()))

def do_download_rpm(yaml : dict, comm : Command) -> Command:
    # data comes in with the form "PRODUCT BRANCH type"
    # where branch can be
    # - "master"
    # - "release-xx.yy"
    # - "release-latest"
    # - "bugfix/PE-xxxxx"
    # - "feature/PE-xxxxx"
    # - "predev/PR-xxx"
    #
    # and type can be
    # - "product"
    # - "tests"
    if comm.data.count(" ") != 2:
        return C(CT.ERROR, "Malformed product string")

    product, branch, typ = comm.data.rstrip().split()

    if typ != "product" and typ != "tests":
        return C(CT.ERROR, "Malformed product string")

    # get urls
    latest_product_url, latest_tests_url = arti.get_latest_rpm_url(product, branch)
    rpm_url = latest_product_url if typ == "product" else latest_tests_url

    if rpm_url == None:
        e = f"Missing {typ} rpm for {product}, {branch}"
        log.error(e)
        return C(CT.ERROR, e)

    # get downloads destination
    # check for env.SERVER_ROOT and fall back on an educated guess
    local_root = os.getenv(env.SERVER_ROOT) if os.getenv(env.SERVER_ROOT) else os.path.dirname(os.path.abspath(__file__)) + "/.."
    local_downloads_path = "/downloads"
    abs_downloads_path = local_root + local_downloads_path
    try:
        os.mkdir(abs_downloads_path)
    except FileExistsError as e:
        pass #ok

    # download, return path relative to local root with a leading slash
    if rpm_url and arti.download_file(rpm_url, abs_downloads_path):
        return C(CT.TASK_FINISHED, local_downloads_path + "/" + os.path.basename(rpm_url))
    else:
        return C(CT.ERROR, f"{product} not found")

def do_install_local_rpm(yaml: dict, comm: Command) -> Command:
    # extract path- should start with / and be relative to local root
    rpm_path = comm.data
    if not rpm_path or not rpm_path.startswith("/"):
        return C(CT.ERROR, f"Bad path: {rpm_path}")

    # check for env.SERVER_ROOT and fall back on an educated guess
    local_root = os.getenv(env.SERVER_ROOT) if os.getenv(env.SERVER_ROOT) else os.path.dirname(os.path.abspath(__file__)) + "/.."

    # install rpm
    if not successful_launch(["which", "rpm"], quiet=True):
        return C(CT.ERROR, "rpm command not found")

    if not successful_launch(["rpm", "-idv", "--nodeps", "--force", f"--prefix={local_root + '/rpminstall'}", f"--dbpath={local_root + '/rpmdb'}", f"{local_root}{rpm_path}"]):
        return C(CT.ERROR, "rpm -idv")

    version = arti.get_local_rpm_version(f"{local_root}{rpm_path}")
    if not version:
        return C(CT.ERROR, "Couldn't find rpm version")

    # point local tests directory to newly installed tests directory
    if "-tests" in rpm_path:
        try:
            local_tests = f"{local_root}/tests"
            if os.path.isfile(local_tests) or os.path.islink(local_tests):
                os.unlink(local_tests)
            elif os.path.isdir(local_tests):
                shutil.rmtree(local_tests)
        except FileNotFoundError as e:
            pass # ok

        product_dirname = os.path.basename(rpm_path)[:os.path.basename(rpm_path).find("-tests")]
        # some product names start with "cray-", but the directories they create
        # have "cray-" omitted
        if product_dirname.startswith("cray-"):
            product_dirname = product_dirname.replace("cray-", "")
        log.debug(f"Deduced directory name: {product_dirname}")

        dst = f"{local_root}/rpminstall/{product_dirname}/{version}/tests"
        log.debug(f"Deduced tests directory location: {dst}")

        try:
            log.debug(f"Creating symlink {local_root}/tests -> {dst}")
            os.symlink(dst, f"{local_root}/tests")
        except Exception as e:
            return C(CT.ERROR, str(e))

    log.info(f"Successfully installed {rpm_path}")

    # return version
    return C(CT.TASK_FINISHED, f"{version}")

def do_module_load(yaml : dict, comm : Command) -> Command:
    args = comm.data
    if args.startswith("latest:"):
        args = args.split(":")
        if len(args) < 2:
            return C(CT.ERROR, f"Invalid argument {args}")

        module = " ".join(args[1:])

        # if we find any modules with versions like xyz/4.9999.1, filter them out
        def filter_weird_versions(mod):
            s = mod.split("/")
            ns = s[1].split(".")
            for n in ns:
                if int(n) > 999:
                    return False
            return True

        avail = [m for m in filter(filter_weird_versions, modules.avail(module))]

        def version_number(mod):
            s = mod.split("/")
            ns = s[1].split(".")
            number = 0
            for n in ns:
                number += int(n)
                number *= 1000
            return number

        # sorted in ascending version order
        avail.sort(key=version_number)

        result = modules.invoke_successfully("load", "".join(avail[-1:]))
        if result:
            return C(CT.TASK_FINISHED, "ok")
        else:
            return C(CT.ERROR, f"Failed to load {args}")
    else:
        # if we already have a version of the specified module loaded,
        # "module load" will fail and we need to use "module swap"

        base_name = args.split("/")[0]
        currently_loaded = modules.list(grep=base_name)

        result = False
        if len(currently_loaded) > 0:
            log.debug(f"Detected {base_name} already loaded, using module swap")
            result = modules.invoke_successfully("swap", args)
        else:
            result = modules.invoke_successfully("load", args)

        if result:
            return C(CT.TASK_FINISHED, "ok")
        else:
            return C(CT.ERROR, f"Failed to load {args}")

def do_module_use(yaml : dict, comm : Command) -> Command:
    args = os.path.expanduser(comm.data)
    result = modules.invoke_successfully("use", args)
    if result:
        return C(CT.TASK_FINISHED, "ok")
    else:
        return C(CT.ERROR, f"Failed to use {args}")

def do_get_module_flavor() -> Command:
    return C(CT.TASK_FINISHED, modules.detect_modules_flavor())

def do_chdir(yaml: dict, comm: Command) -> Command:
    comm.data = os.path.expanduser(comm.data)

    log.info(f"Changing cwd to {comm.data}")

    try:
        os.chdir(comm.data)
    except FileNotFoundError as e:
        return C(CT.ERROR, str(e))

    os.environ["PWD"] = os.getcwd()

    return C(CT.TASK_FINISHED, comm.data)

def do_quit(yaml : dict, comm : Command) -> Command:
    log.info("Quitting")
    # remove test keys from authorized_keys

    lock_filename = "/tmp/cdst_test_authorized_keys_lock"
    log.debug("Trying to get authorized_keys lock")
    with open(lock_filename, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        log.debug("Got lock")

        key_id = comm.data
        log.info(f"Removing test key \"{key_id}\" from authorized keys")
        if key_id != "":
            home = os.getenv("HOME")
            try:
                with open(f"{home}/.ssh/authorized_keys", "r") as old:
                    with open(f"{home}/.ssh/authorized_keys.tmp", "w") as new:
                        for line in old:
                            # re-write every key *except* ours to the new file
                            if ssh.ONE_OFF_KEY_COMMENT not in line or f"id {key_id}" not in line:
                                new.write(line)
                os.replace(f"{home}/.ssh/authorized_keys.tmp", f"{home}/.ssh/authorized_keys")
            except FileNotFoundError as e:
                log.warn(f"{home}/.ssh/authorized_keys not found. Can't clean up keys")
        else:
            log.warn(f"Couldn't remove ssh key from authorized keys: blank id.")

        # lock released upon closing the fd

    try:
        os.unlink(lock_filename)
    except FileNotFoundError:
        pass # already gone, that's ok

    return C(CT.TASK_FINISHED, "Server is quitting")

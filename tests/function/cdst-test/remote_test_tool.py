#!/usr/bin/env python3

import functools
import os
import threading
import re
import socket
import time
import termios
import sys
import yaml
import pathlib

from typing import Union

# add cwd to python import path so when we change working directories we can still import cdst_test
if os.path.isdir("./cdst_test"):
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import cdst_test.remote_test_tool_startup as startup
import cdst_test.remote_test_tool_ui as ui

from cdst_test.test_server_proto import Command, CommandType, MAX_REQUEST_LEN, command_from_bytes
import cdst_test.log as log
import cdst_test.ssh as ssh
import cdst_test.files as files
import cdst_test.test_server_proto as proto
import cdst_test.artifactory as arti
import cdst_test.env as env

class TestResult():
    RESULT_unknown = 0
    RESULT_ok = 1
    RESULT_failed = 2
    RESULT_invalid = 3
    RESULT_skipped = 4

    def __init__(self, result) -> None:
        self.name = "?" # name of test that this result corresponds to
        self.result = result

        if self.result < 0 or self.result >= self.RESULT_invalid:
            raise RuntimeError

class TestContext():
    # holds data for each thread running tests on remote machines

    STATE_print = 1 # simple print mode
    STATE_consume_results = 2 # print a progress bar as test results come in
    STATE_finish_up = 3 # print the completed progress bar plus an aditional string

    class ServerBehavior():
        """
        Passed lists should hold strings of the form "product:version".
        See global -I option.
        Install_tests should be a product:branch string or None
        """
        def __init__(self, install_product: "List[str]", install_tests: str,
            module_use: "List[str]", module_load: "List[str]"):
            # server side behavior
            self.install_product = install_product
            self.install_tests = install_tests
            self.module_use = module_use
            self.module_load = module_load

    def __init__(self, exit_flag: threading.Event, ssh: ssh.SshContext, behavior: ServerBehavior, avo_config: str):
        self.thread = None
        self.ssh = ssh
        self.behavior = behavior
        self.exit_flag = exit_flag
        self.avo_config = avo_config

        self.state = self.STATE_print

        self.results = []     # list of TestResult
        self.results_collected = 0
        self.finished_normally = False

        self.ui_status = "Not started"
        self.tty_mode = True

    def start_thread(self):
        location = f"{self.ssh.host()}"
        location_detail = f" ({self.ssh.get_friendly_name()})"
        location_str = f"{location}{location_detail if self.ssh.get_friendly_name() != location else ''}"

        if self.ssh.ssh_good:
            self.thread = threading.Thread(target=run_remote_tests, args=(self,))
            log.info(f"Starting tests on {location_str}...")
            self.thread.start()
        else:
            log.info(f"Skipping {location_str}...")

    # feed the context a log message, updating internal status
    def feed(self, string : str, level : int):
        if level < 4:
            self.ui_status = string

            if self.state == self.STATE_consume_results:
                result = TestResult(TestResult.RESULT_unknown)
                if string.startswith("ok"):
                    if "# SKIP" in string:
                        result.result = TestResult.RESULT_skipped
                    else:
                        result.result = TestResult.RESULT_ok
                    string = string.replace("ok ", "")
                    self.results_collected += 1
                elif string.startswith("not ok"):
                    result.result = TestResult.RESULT_failed
                    string = string.replace("not ok ", "")
                    self.results_collected += 1

                # move past test number
                string = string[string.find(" ") + 1:]

                result.name = string

                self.results[self.results_collected - 1] = result

                if len(self.results) == self.results_collected:
                    self.state = self.STATE_finish_up
            elif self.state == self.STATE_finish_up:
                pass
            else: # STATE_print
                if string.startswith("1.."):
                    # start the progress bar
                    self.state = self.STATE_consume_results
                    self.gen_results_array(int(string[3:]))

    def gen_results_array(self, n : int):
        for _ in range(n):
            self.results.append(TestResult(TestResult.RESULT_unknown))

    def get_status_str(self):
        return self.ui_status

def write_summary(contexts : "list[TestContext]", filename : str):
    if len(contexts) < 1:
        log.debug("Nothing to summarize")
        return

    log.info(f"Summarizing results in {filename}...")

    with open(filename, "w") as f:
        f.write("Tests listed here passed unless otherwise noted.\n\n")

        for ctx in contexts:
            header = ctx.ssh.get_friendly_name() + " " + ("-" * (80 - len(ctx.ssh.get_friendly_name()) - 1))
            f.write(header + "\n")

            if not ctx.finished_normally:
                f.write("Did not finish because of error...\n")

            for result in ctx.results:
                # build result line
                line = ""

                if result.result == TestResult.RESULT_ok:
                    line += "     "
                elif result.result == TestResult.RESULT_failed:
                    line += "FAIL "
                elif result.result == TestResult.RESULT_skipped:
                    line += "SKIP "
                else:
                    line += "?    "

                line += result.name

                f.write(f"{line}\n")
            f.write("\n")

def analyze_results(contexts : "list[TestContext]", filename: str):
    # FIXME: since we started running tests in parallel, result order is undefined.
    #        this breaks a lot of assumptions this function once had and leads to
    #        reports that say "x test failed on every machine" where x is the incorrect name
    if len(contexts) < 1:
        log.debug("Nothing to analyze")
        return

    log.info("Analyzing results...")
    log.info("")

    # filter out any contexts that didn't finish tests
    filtered = [f for f in filter(lambda ctx: len(ctx.results) > 0, contexts)]

    hosts_headers = [ctx.ssh.get_friendly_name() for ctx in filtered]
    hosts_data = yaml.safe_load(open(files.data() + "/hosts.yaml", "r"))

    results_matrix = zip(*[ctx.results for ctx in filtered])

    log.debug(f"host headers: {hosts_headers}")

    with open(filename, "a") as file:
        def tee(message : str):
            log.info(message)

            # remove any color codes from the message
            message = message.replace("\u001b[1m\u001b[31m", "")
            message = message.replace("\u001b[0m", "")
            file.write(message + "\n")

        for i, results_tuple in enumerate(results_matrix):
            # if no failure, continue
            some_failed = sum([r.result == TestResult.RESULT_failed for r in results_tuple]) > 0
            if not some_failed: continue

            # check if test failed on every machine
            all_failed = sum([r.result == TestResult.RESULT_ok for r in results_tuple]) == 0
            if all_failed:
                if log._get_thread_local_logger().file.isatty() or log._get_thread_local_logger().tee == True:
                    red = "\u001b[1m\u001b[31m"
                    none = "\u001b[0m"
                else:
                    red = ""
                    none = ""
                on_every_machine = f" {red}on every machine{none}" if len(results_tuple) > 1 else ""
                tee(f"!!! Test {i + 1}, {results_tuple[0].name}, failed{on_every_machine}")
                continue

            # check if test failed on every machine with a particular wlm
            def check_for_common_failures(key):
                possible_values = []
                for hostname in hosts_headers:
                    host = hosts_data[hostname] if hostname in hosts_data else None
                    if host:
                        value = host[key]
                        if value not in possible_values: possible_values.append(value)

                for value in possible_values:
                    # try to find a single test that has a matching value that passed
                    at_least_one_passed = False
                    # don't conflict with the i in the outside scope
                    for j, result in enumerate(results_tuple):
                        hostname = hosts_headers[j]
                        host_data = hosts_data[hostname] if hostname in hosts_data else None

                        if host_data and host_data[key] == value and result.result == TestResult.RESULT_ok:
                            at_least_one_passed = True
                            break

                    if not at_least_one_passed:
                        tee(f"    Test {i + 1}, {results_tuple[0].name}, failed on every machine where {key} = {value}")

            check_for_common_failures("wlm")
            check_for_common_failures("type")
            check_for_common_failures("arch")

        tee("")

def connect_to_test_server(port : int, exit_flag: threading.Event, test_attempt = 1, max_test_attempts = 10, log_message = "Connecting to test server"):
    max_tunnel_attempts = 10
    connect_tunnel_attempt = 1
    sock = socket.socket()

    if exit_flag.is_set():
        # short circuit
        log.debug("Short circuiting connecting to test server (exit flag)")
        return None

    while True:
        try:
            log.info(f"Connecting to ssh tunnel... ({connect_tunnel_attempt}/{max_tunnel_attempts})")
            # use ssh tunnel
            sock.connect(("localhost", port))
            break
        except ConnectionRefusedError as e:
            connect_tunnel_attempt += 1
            if connect_tunnel_attempt > max_tunnel_attempts:
                return None
            time.sleep(3)

    # since we're using ssh tunnels, sock.connect will always succeed, but if the
    # server isn't really there, it will fail upon first receive. (Connection reset by peer)

    # check if we're REALLY connected
    ack = Command(CommandType.ACK, "knock knock")
    sock.sendall(ack.encode())
    try:
        chunk = sock.recv(MAX_REQUEST_LEN)
    except ConnectionResetError as e:
        # try again...
        if test_attempt < max_test_attempts:
            log.warn(f"{log_message}... ({test_attempt}/{max_test_attempts})")
            sock.close()
            time.sleep(3)
            return connect_to_test_server(port, exit_flag, test_attempt + 1, max_test_attempts, log_message)
        else:
            # failed too many times!
            return None

    if chunk == b'':
        log.error("Received blank results from server.")
        return None

    re_list, _ = proto.extract_commands_from_chunk(chunk)
    if len(re_list) != 1:
        return None

    re = command_from_bytes(re_list[0])
    if re.command_type != CommandType.ACK:
        return None

    log.info("Connected to test server.")
    return sock

class RemoteTestToolError(Exception):
    def __init__(self, err):
        self.err = err

# helper function to install rpms
# typ should be "product" or "tests"
# on successful install, returns version ("1.2.3.4") of install rpm
# on error, returns None
def rpm_install_sequence(hostname, product, branch, typ: str, ctx, sock) -> str:
    connection_test = proto.send_task_and_wait(sock, Command(CommandType.TEST_ARTI_CONNECTION), ctx.exit_flag)
    if connection_test is None:
        return None

    if typ != "product" and typ != "tests":
        log.error(f"Invalid rpm type: {typ}")
        return None

    # will start with / and be local to ctx.ssh.remote_tests_root()
    remote_rpm_path = None

    if connection_test == "True":
        log.info("Downloading server side")
        # server can handle it from here
        remote_rpm_path = proto.send_task_and_wait(sock, Command(CommandType.DOWNLOAD_RPM, f"{product} {branch} {typ}"), ctx.exit_flag)
        if not remote_rpm_path:
            log.error(f"Error during tests install ({product} {branch}). Halting tests.")
            return None

        # fall out of if statement and install it
    else:
        # server can't see arti, need to download locally and deliver ourselves
        log.info("Downloading client side")

        # can we see arti?
        if not arti.test_artifactory_visibility():
            log.error("Can't see artifactory from client")
            return None

        # what os folder in arti should we look in for the server?
        os_folder = proto.send_task_and_wait(sock, Command(CommandType.GET_ARTI_OS), ctx.exit_flag)
        if not os_folder:
            log.error("Couldn't find repo path")
            return None

        # what's the full repo path for this product, branch, and os combo?
        repo_path = arti.get_arti_repo(branch, os_folder)
        if not repo_path:
            log.error(f"Counldn't determine repo path for {branch}, {os_folder}")
            return None

        # what are the urls?
        prod_url, tests_url = arti.get_latest_rpm_url(product, branch, repo_path)
        # the url we are interested in
        rpm_url = prod_url if typ == "product" else tests_url

        # download them locally
        downloads_path = "./cdst_tests_downloads/" + hostname
        pathlib.Path(downloads_path).mkdir(parents=True, exist_ok=True)

        if not arti.download_file(rpm_url, downloads_path):
            log.error(f"failed to download {rpm_url}")
            return None

        # push to remote machine /downloads
        if not ctx.ssh.scp_push(downloads_path + "/" + os.path.basename(rpm_url), "/downloads"):
            log.error(f"Error pushing rpm {rpm_url}")
            return None

        remote_rpm_path = "/downloads/" + os.path.basename(rpm_url)

    # at this point, the rpm has made it to the remote /downloads folder
    # return rpm version
    return proto.send_task_and_wait(sock, Command(CommandType.INSTALL_LOCAL_RPM, remote_rpm_path), ctx.exit_flag)

def run_remote_tests(ctx : TestContext):
    # running remote tests happens in two steps. the first step is to setup the remote
    # testing directory and download/transfer any product rpms/tests. this step doesn't
    # require any mpi/allocations since it only writes files.
    #
    # the second step is to allocate nodes and run the tests. in order for the remote
    # tool to allocate nodes, it has to restart itself under a parent salloc or qsub etc.
    # process. this restart breaks our initial connection to the test tool, so we need
    # to immediately reconnect.

    try:
        os.mkdir(log.get_log_dir() + f"/{ctx.ssh.get_friendly_name()}")
    except FileExistsError:
        pass

    log._LOG_THREAD_LOCAL.log = log.new_log_file(f"{ctx.ssh.get_friendly_name()}/client.log")

    h = functools.partial(TestContext.feed, ctx)
    log.set_hook(h)

    log.info(f"Setting up remote tests directory ({ctx.ssh.remote_tests_root()})")
    if not ctx.ssh.setup_remote_tests_root():
        log.error(f"Failed to set up remote tests directory ({ctx.ssh.remote_tests_root()})")
        return False

    try:
        tunnel = ctx.ssh.start_ssh_tunnel()

        # --- start step 1: download/transfer rpms and test files ------------------------

        log.info(f"Starting remote test server ({ctx.ssh.host()}, port {ctx.ssh.port()})")
        server = ctx.ssh.start_remote_server()

        # sanity check: server thread should be running at this point.
        # If it's not, the server probably failed to start
        if not server.is_alive():
            raise RemoteTestToolError("Server failed to start. Exiting.")

        log.info(f"Obtaining test files")

        sock = connect_to_test_server(ctx.ssh.port(), ctx.exit_flag)
        if not sock:
            raise RemoteTestToolError("Failed to connect to test server. Exiting.")

        # install rpms from arti if specified
        for productstr in ctx.behavior.install_product:
            if productstr.count(":") == 1:
                product, branch = productstr.split(":")
                log.info(f"Installing {product} ({branch})...")
                version = rpm_install_sequence(ctx.ssh.get_friendly_name(), product, branch, "product", ctx, sock)
                if not version:
                    raise RemoteTestToolError(f"Error during product install ({product} {branch}). Halting tests.")
            else:
                log.warning(f"Warning: bad product string {productstr}. Ignoring.")

        # install test rpms
        if ctx.behavior.install_tests and ctx.behavior.install_tests.count(":") == 1:
            product, branch = ctx.behavior.install_tests.split(":")
            log.info(f"Installing tests {product} ({branch})...")
            rpm_version = rpm_install_sequence(ctx.ssh.get_friendly_name(), product, branch, "tests", ctx, sock)
            if not rpm_version:
                raise RemoteTestToolError(f"Error during product install ({product} {branch}). Halting tests.")

        # change working yaml to yaml in tests directory
        if not proto.send_task_and_wait(sock, Command(CommandType.YAML_PATH, ctx.ssh.remote_tests_root() + "/tests/test_tool_config.yaml"), ctx.exit_flag):
            raise RemoteTestToolError("Error changing yaml path")

        # allocate nodes. this will break our connection!!!
        if not proto.send_task_and_wait(sock, Command(CommandType.DO_SETUP_ENV), ctx.exit_flag):
            raise RemoteTestToolError("Error getting allocation")

        sock.close()
        log.info("First socket closed")

        # --- start step 2: wait for allocation, reconnect, and run tests ----------------
        log.info(f"Reconnecting to remote test server ({ctx.ssh.host()}, port {ctx.ssh.port()})")
        sock = connect_to_test_server(ctx.ssh.port(), ctx.exit_flag, max_test_attempts=100, log_message="Waiting for allocation")

        if not sock:
            raise RemoteTestToolError("Failed to connect to test server after allocation. Exiting.")

        # get module flavor of remote machine. this affects where modulefiles are located
        remote_mod_flavor = proto.send_task_and_wait(sock, Command(CommandType.GET_MODULES_FLAVOR), ctx.exit_flag)
        if remote_mod_flavor != "tmod" and remote_mod_flavor != "lmod":
            raise RemoteTestToolError(f"Unknown modules flavor: {remote_mod_flavor}")

        # module use installed rpms
        if len(ctx.behavior.install_product) > 0:
            if remote_mod_flavor == "tmod":
                if not proto.send_task_and_wait(sock, Command(CommandType.MODULE_USE, ctx.ssh.remote_tests_root() + "/rpminstall/modulefiles"), ctx.exit_flag):
                    raise RemoteTestToolError("Error during module use. Halting tests.")
            elif remote_mod_flavor == "lmod":
                if not proto.send_task_and_wait(sock, Command(CommandType.MODULE_USE, ctx.ssh.remote_tests_root() + "/rpminstall/lmod/modulefiles/core"), ctx.exit_flag):
                    raise RemoteTestToolError("Error during module use. Halting tests.")
            else:
                raise RemoteTestToolError(f"Unknown modules flavor: {remote_mod_flavor}")

        # module load load installed rpms
        for productstr in ctx.behavior.install_product:
            if productstr.count(":") == 1:
                product, branch = productstr.split(":")
                log.info(f"Loading {product} ({branch})...")
                version = rpm_install_sequence(ctx.ssh.get_friendly_name(), product, branch, "product", ctx, sock)
                if not proto.send_task_and_wait(sock, Command(CommandType.MODULE_LOAD, f"{product}/{version}"), ctx.exit_flag):
                    raise RemoteTestToolError("Error during module loading ({product} {branch}). Halting tests.")

        # module use anything specified on the command line
        for usestr in ctx.behavior.module_use:
            if not proto.send_task_and_wait(sock, Command(CommandType.MODULE_USE, usestr), ctx.exit_flag):
                raise RemoteTestToolError("Error during module use. Halting tests.")

        # module load anything specified on the command line
        for loadstr in ctx.behavior.module_load:
            if not proto.send_task_and_wait(sock, Command(CommandType.MODULE_LOAD, loadstr), ctx.exit_flag):
                raise RemoteTestToolError("Error during module loading. Halting tests.")

        # change working yaml to yaml in tests directory
        if not proto.send_task_and_wait(sock, Command(CommandType.YAML_PATH, ctx.ssh.remote_tests_root() + "/tests/test_tool_config.yaml"), ctx.exit_flag):
            raise RemoteTestToolError("Error changing yaml path")
        # chdir to ./tests
        if not proto.send_task_and_wait(sock, Command(CommandType.CHDIR, ctx.ssh.remote_tests_root() + "/tests"), ctx.exit_flag):
            raise RemoteTestToolError(f"Failed to chdir to {ctx.ssh.remote_tests_root() + '/tests'}")
        # clean up
        if not proto.send_task_and_wait(sock, Command(CommandType.DO_CLEAN), ctx.exit_flag):
            raise RemoteTestToolError("Error during cleanup. Halting tests.")
        # do sanitiy checks
        if not proto.send_task_and_wait(sock, Command(CommandType.DO_SANITY_CHECKS), ctx.exit_flag):
            raise RemoteTestToolError("Failed sanity checks. Halting tests.")
        # build tests
        if not proto.send_task_and_wait(sock, Command(CommandType.DO_BUILD), ctx.exit_flag):
            raise RemoteTestToolError("Failed build. Halting tests.")
        # run tests
        if not proto.send_task_and_wait(sock, Command(CommandType.DO_TESTS, ctx.avo_config), ctx.exit_flag):
            raise RemoteTestToolError("Error during test running. Halting tests.")

        ctx.finished_normally = True

    except RemoteTestToolError as rtte:
        log.error(f"Remote test tool error: {rtte.err}")
        log.error("Shutting down")
        return False
    except Exception as e:
        log.error(f"Uncaught exception: {str(e)}")
        log.error("Shutting down")
        return False

    finally:
        # retrieve logs before shutting down the server since shutting
        # down the server will remove any keys we sent over, locking us out
        log.info("Retrieving logs...")
        if not ctx.ssh.scp_pull("/logs/", log.get_log_dir() + f"/{ctx.ssh.get_friendly_name()}/remote", recursive = True):
            log.warn("Failed to retrieve server logs...")
        if not ctx.ssh.scp_pull("/tests/avocado-virtual-environment/job-results/latest/job.log",
            log.get_log_dir() + f"/{ctx.ssh.get_friendly_name()}/job.log"):
            log.warn("Failed to retrieve job.log...")
        if ctx.ssh.scp_pull("/tests/avocado-virtual-environment/job-results/latest/results.xml",
            log.get_log_dir() + f"/{ctx.ssh.get_friendly_name()}/results.xml"):
            # annotate test names in results.xml with the hostname they came from
            # so that tools that aggregate all tests won't have duplicate test names
            log.debug("Annotating results.xml")
            old_xml = ""
            with open(log.get_log_dir() + f"/{ctx.ssh.get_friendly_name()}/results.xml", "r") as old_xml_file:
                old_xml = old_xml_file.read()
            # replaces 'classname="..."' with 'classname="hostname"'
            new_xml = re.sub(r'(<testcase.*classname=\")(.*?)(\"\s.*/?>)', f'\\1{ctx.ssh.get_friendly_name()}\\3', old_xml)
            with open(log.get_log_dir() + f"/{ctx.ssh.get_friendly_name()}/results.xml", "w") as new_xml_file:
                new_xml_file.write(new_xml)
        else:
            log.warn("Failed to retrieve results.xml...")
        if not ctx.ssh.scp_pull("/tests/tmp", log.get_log_dir() + f"/{ctx.ssh.get_friendly_name()}/tmp", recursive = True):
            log.warn("Failed to retrieve tmp...")
        if not ctx.ssh.scp_pull("/tests/tests.py.data", log.get_log_dir() + f"/{ctx.ssh.get_friendly_name()}/tests.py.data", recursive = True):
            log.warn("Failed to retrieve tests.py.data...")

        if sock:
            if not proto.send_task_and_wait(sock, Command(CommandType.QUIT, ctx.ssh.conn_i.local_key_id), ctx.exit_flag):
                log.error("Error during server quit.")
            sock.close()

        timeout = 20
        log.info(f"Waiting {timeout} seconds for the test server to shut down...")
        # ssh connection thread should naturally finish when the server on the other side finishes
        server.wait(timeout)
        server.kill()

        log.info("Waiting for the ssh tunnel to shut down...")
        tunnel.kill()

        log.info(f'Done{", with possible errors. Check logs." if not ctx.finished_normally else ""}')

        return True

def create_and_verify_test_contexts(user, hosts, first_port, key,
    install_product, tests_source, module_use, module_load, avo_config,
    clean_old, manual_server, id_str, exit_flag) -> "list[TestContext]":

    hosts_data = yaml.safe_load(open(files.data() + "/hosts.yaml", "r"))
    contexts = []

    log.info("Setting up connections...")
    log.info(f"Starting on port {first_port}")
    for host in hosts:
        log.info(f"{host}...")
        log.indent()
        is_uai = False
        remote_dir = None

        # parse host string to determine uai/custom directory
        if host.startswith("uai:"):
            host = host.replace("uai:", "")
            is_uai = True

        if ":" in host:
            if host.count(":") > 1:
                log.error(f"Invalid host string: {host}. Too many colons. Skipping.")
                continue
            remote_dir = host[host.rfind(":") + 1:]
            host = host.replace(":" + remote_dir, "")
            remote_dir = remote_dir.replace("%%user%%", user)
            log.info(f"Using {remote_dir} on {host}")

        # tell ssh about the host's alias, if it has one
        human_friendly_name = None
        if host in hosts_data and "hostname" in hosts_data[host]:
            log.warn(f"\"{host}\" -> {hosts_data[host]['hostname']}")
            human_friendly_name = host
            host = hosts_data[host]["hostname"]

        # if tests_source is a PRODUCT:BRANCH string, installation will be done
        # at server run time, so don't pass anything to ssh.
        local_tests_source = None
        if "/" in tests_source and ":" not in tests_source:
            local_tests_source = tests_source
        else:
            log.debug(f"Defering tests installation until server is up")

        connection_info = ssh.SshContext.ConnectionInfo(user, host, human_friendly_name, first_port, key)
        paths_info = ssh.SshContext.TestPathsInfo(
            local_remote_ttool_path=os.path.abspath(__file__),
            local_ttool_path=os.path.abspath(os.path.dirname(__file__) + "/test_tool.py"),
            local_tlib_path=os.path.abspath(os.path.dirname(__file__) + "/cdst_test"),
            local_tests_path=local_tests_source,
            remote_tests_root=remote_dir
        )
        uai_info = ssh.SshContext.UaiInfo(host) if is_uai else None

        ssh_ctx = ssh.SshContext(connection_info, paths_info, uai_info, clean_old, manual_server, id_str)
        first_port += 1
        if ssh_ctx.setup_ssh_connectivity():
            log.info(f"Connection to {host} is good.")
            ssh_ctx.ssh_good = True
        else:
            log.warn(f"Connection to {host} could not be established, bypassing.")
            ssh_ctx.ssh_good = False

        install_tests = tests_source if ":" in tests_source else None

        bvr = TestContext.ServerBehavior(
            install_product=install_product, install_tests=install_tests,
            module_use=module_use, module_load=module_load
        )

        contexts.append(TestContext(exit_flag, ssh_ctx, bvr, avo_config));

        log.outdent()

    return contexts

def main():
    immediate_exit_code = startup.parse_early_exit_args()
    if immediate_exit_code is not None:
        return immediate_exit_code

    try:
        # connection info
        # product/test installation/source info
        # server side behavior info
        # misc info
        user, hosts, first_port, key, \
        install_product, tests_source, module_use, module_load, avo_config, \
        clean_old, manual_server, \
        id_str, = startup.parse_arguments()
    except RuntimeError:
        startup.get_arg_parser().print_usage()
        return False

    log.info("Selected hosts:")
    log.indent()
    for host in hosts:
        log.info(f"{host}")
    log.outdent()
    log.info("")

    # ssh subprocesses can mess up terminal settings - these will be restored on exit
    if sys.stdin.isatty():
        old_stdin = termios.tcgetattr(sys.stdin.fileno())
    if sys.stdout.isatty():
        old_stdout = termios.tcgetattr(sys.stdout.fileno())
    if sys.stderr.isatty():
        old_stderr = termios.tcgetattr(sys.stderr.fileno())

    global_exit_flag = threading.Event()

    try:
        all_test_contexts = create_and_verify_test_contexts(
            user=user, hosts=hosts, first_port=first_port, key=key,
            install_product=install_product, tests_source=tests_source,
            module_use=module_use, module_load=module_load, avo_config=avo_config,
            clean_old=clean_old, manual_server=manual_server,
            id_str=id_str, exit_flag=global_exit_flag
        )

        try:
            for ctx in all_test_contexts:
                ctx.start_thread()

            def num_threads_alive():
                return len([tr for tr in all_test_contexts if tr.thread and tr.thread.is_alive()])

            gui = ui.get_default_ui(all_test_contexts)

            # if debug is turned on, check status more often
            frame_wait = .2 if not os.getenv(env.DEBUG) else 1/24 # 24 fps for a cinematic experience

            gui.prepare()
            while num_threads_alive() and not global_exit_flag.is_set():
                gui.display()
                global_exit_flag.wait(frame_wait)
            gui.finish()

            for ctx in all_test_contexts:
                if ctx.thread:
                    ctx.thread.join()

            summary_filename = log.get_log_dir() + "/summary.txt"
            write_summary(all_test_contexts, summary_filename)
            # FIXME: analyze_results is currently broken, see FIXME comment with the function
            # analyze_results(all_test_contexts, summary_filename)
        except KeyboardInterrupt:
            log.warn("Caught keyboard interrupt, signalling threads to shut down...")
            global_exit_flag.set()
        finally:
            for ctx in all_test_contexts:
                if ctx.thread:
                    # if early exiting, be verbose
                    if global_exit_flag.is_set():
                        log.info(f"{ctx.ssh.get_friendly_name()}...")
                    ctx.thread.join()

            log.info("Cleaning up...")
            for ctx in all_test_contexts:
                log.info(f"{ctx.ssh.get_friendly_name()}...")
                log.indent()
                ctx.ssh.cleanup()
                log.outdent()

            log.info("")
            log.info(f"Check logs and results in {log.get_log_dir()}")
    finally:
        # ssh subprocesses can mess up terminal settings
        if sys.stdin.isatty():
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_stdin)
        if sys.stdout.isatty():
            termios.tcsetattr(sys.stdout, termios.TCSADRAIN, old_stdout)
        if sys.stderr.isatty():
            termios.tcsetattr(sys.stderr, termios.TCSADRAIN, old_stderr)

    return True

if __name__ == "__main__":
    exit(0 if main() else -1)

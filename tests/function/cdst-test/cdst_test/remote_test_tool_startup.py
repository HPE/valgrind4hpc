# Copyright 2021 Hewlett Packard Enterprise Development LP
#
# Startup functions such as arg parsing for the remote test too client

import argparse, yaml, getpass, random, os, re

from typing import Union

import cdst_test.log as log
import cdst_test.files as files
import cdst_test.test_server as server
import cdst_test.env as env

def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run functional tests remotely")

    # connection args
    parser.add_argument("-p", "--port", help="Bypass random port selection and make the remote testing servers listen on ports starting at PORT and incrementing.", metavar="PORT")
    parser.add_argument("-u", "--user", help="Run remote tests as USER instead of the currently logged in user.", metavar="USER")
    parser.add_argument("-k", "--ssh-key", help="Path to an ssh private key file to use to connect instead of generating one.", metavar="PATH")

    # auto host selection args
    parser.add_argument("-l", "--list-hosts", help="Auto generate hosts list based on o/O/q arguments, print it, and exit.", action="store_true")
    parser.add_argument("-L", "--list-qualities", help="List known qualities available for q argument and exit.", action="store_true")
    parser.add_argument("-I", "--list-products", help="List known products that can be used as PRODUCT in --install and exit.", action="store_true")
    parser.add_argument("-o", "--on-host", help="Add HOST to selected hosts. Can be used multiple times. To create a uai, prefix the hostname with \"uai:\". To specify a base directory for tests, postfix the host with \":directory_name\". e.g. \"-o uai:monster-ncn-w001:/lus/username/tmp\".", metavar="HOST", action="append")
    parser.add_argument("-O", "--off-host", help="Removes HOST from selected hosts. Can be used more than once.", metavar="HOST", action="append")
    parser.add_argument("-q", "--qualities", help="Auto detect hosts set by selecting hosts matching QUALEXPR. Use the -L option to see examples.", metavar="QUALEXPR")

    # test and product related args
    parser.add_argument("-t", "--tests", help="Local PATH to directory containing test_tool_starter.py and tests.py, or a PRODUCT:BRANCH string to download them from artifactory, see -I for valid options.", metavar="PATH or PRODUCT:BRANCH")
    parser.add_argument("-i", "--install", help="Tell the test server to install a product from artifactory. Can be used multiple times. See -I for more info.", metavar="PRODUCT:BRANCH", action="append")
    parser.add_argument("-b", "--bundle", help="Shorthand for passing PRODUCT:BRANCH to -t and -i at the same time.", metavar="PRODUCT:BRANCH")
    parser.add_argument("-m", "--module", "--product", help="Load MODULE on the remote machine before testing. Valid formats are \"MODULE\" (loads default), \"MODULE/1.2.3\", and \"latest:MODULE\" (loads latest).", metavar="MODULE")
    parser.add_argument("-s", "--module-use", help="Call \"module use PATH\" on the remote machine before loading modules.", metavar="PATH")
    parser.add_argument("-c", "--config", help="When running tests, use FILENAME in place of the default avocado_config.yaml file.", metavar="FILENAME")

    # misc/debug args
    parser.add_argument("--debug", help=f"Turn debug output on. Has the same effect as setting {env.DEBUG}.", action="store_true")
    parser.add_argument("--manual-server", help="Don't start the testing server automatically. Assume that it has already been started on the remote machine.", action="store_true")
    parser.add_argument("--server-port", help="Run the test tool in server mode, listening on PORT", metavar="PORT")
    parser.add_argument("--id-string", help="Don't generate a unique id string for keys, directories, etc. Instead, use IDSTRING.", metavar="IDSTRING")
    parser.add_argument("--clean-old", help="Before testing, remove test directories more than 1 week old.", action="store_true")
    parser.add_argument("--log-mode", help="Redirect all output to a log file.", action="store_true")
    parser.add_argument("--color-test", help="Test colors and then exit.", action="store_true")
    parser.add_argument("--slack-msg", help="Read ./logs and print a summary message appropriate for a slack message and then exit", action="store_true")

    return parser

# take passed argv and figure out which hosts we should run tests on
def determine_hosts(args: argparse.Namespace) -> set:
    hosts_data = yaml.safe_load(open(files.data() + "/hosts.yaml", "r"))
    del hosts_data["SCHEMA"]

    chosen_hosts = set()

    if args.qualities:
        chosen_hosts = parse_qualities_expr(args.qualities)

    # add any explicitly specified hosts
    if args.on_host: chosen_hosts |= set(args.on_host)

    # remove any explicitly specified hosts
    if args.off_host: chosen_hosts -= set(args.off_host)

    # turn a hostname into a string usable by the the program including
    # - uai tag if needed
    # - cwd tag if needed

    def tag_hostname(hostname):
        if hostname not in hosts_data: return hostname

        untagged_hostname = hostname
        host_type = hosts_data[untagged_hostname]["type"]

        if not untagged_hostname.startswith("uai:") and "shasta-type" in hosts_data[untagged_hostname] and hosts_data[untagged_hostname]["shasta-type"] == "ncn":
            hostname = "uai:" + hostname

        if "cwd" in hosts_data[untagged_hostname]:
            hostname = hostname + ":" + hosts_data[untagged_hostname]["cwd"]

        return hostname

    return set([tag_hostname(hostname) for hostname in chosen_hosts])

# parse and handle arguments that result in early exits such as the --list-XYZ args
def parse_early_exit_args() -> Union[bool, None]:
    args = get_arg_parser().parse_args()

    if args.server_port:
        # run in server mode
        log.warn("Running in server mode")
        return server.main(args)

    if args.list_hosts:
        hosts = determine_hosts(args)
        log.info("Selected hosts:")
        log.indent()
        for host in hosts:
            log.info(f"{host}")
        log.outdent()
        log.info("")
        log.info("Exiting.")
        return True

    if args.list_products:
        list_products()
        log.info("Exiting.")
        return True

    if args.list_qualities:
        list_qualities()
        log.info("Exiting.")
        return True

    if args.slack_msg:
        print_slack_message()
        log.info("Exiting.")
        return True

    if args.color_test:
        color_test()
        log.info("Exiting.")
        return True

    return None

# Parse passed argv and return a huge tuple of parsed/deduced values.
def parse_arguments() -> tuple:
    args =  get_arg_parser().parse_args()

    if args.debug:
        os.environ[env.DEBUG] = "1"

    # connection details
    user = getpass.getuser()
    if args.user:
        user = args.user

    hosts = determine_hosts(args)
    if not hosts:
        log.error("No hosts found. Specify hosts with the -o, -O, and -q options.")
        raise RuntimeError()

    first_port = random.randint(20000, 40000)
    if args.port:
        first_port = int(args.port)

    key = args.ssh_key if args.ssh_key else None

    # product/test installation/source details
    if args.tests and args.bundle:
        log.error("Can't use --bundle with --tests. (Only one set of tests can be specified.) Use either --bundle alone or --tests and/or --install together.")
        raise RuntimeError()

    install_product = []
    if args.install:
        for p in args.install:
            install_product.append(p)

    tests_source = None
    if args.tests:
        tests_source = args.tests
    elif not args.bundle:
        tests_source = "./tests"
        log.info(f"Using default tests source {tests_source}.")

    if args.bundle:
        install_product.append(args.bundle)
        tests_source = args.bundle

    module_use = [args.module_use] if args.module_use else []
    module_load = [args.module] if args.module else []

    avo_config = args.config if args.config else "avocado_config.yaml"

    # server side behavior details
    clean_old = args.clean_old
    manual_server = args.manual_server

    id_str = None
    if args.id_string is not None:
        id_str = args.id_string
        log.info(f"Using user passed id string \"{id_str}\"")

    args = (user, hosts, first_port, key,
        install_product, tests_source, module_use, module_load, avo_config,
        clean_old, manual_server, id_str)

    log.debug(f"Parsed args: {args}")
    return args

# Take the schema dictionary from hosts.yaml and the dictionary of all the hosts
# from hosts.yaml and product a set of hosts for each possible host quality.
#
# e.g. Among the results dictionary will have a key called "xc" which will map
# to a list of all hostnames that are xc.
def get_qualities_sets(schema: dict, hosts_data: dict) -> dict:
    sets = {}

    # build sets, one set for each possible quality
    for schema_key, schema_value in schema.items():
        # don't process non-list qualities
        if not isinstance(schema_value, list): continue

        for quality in schema_value:
            this_set = set()
            for hostname, host in hosts_data.items():
                if schema_key in host and host[schema_key] == quality:
                    this_set.add(hostname)
            sets[quality] = this_set

    return sets

# Take a "quality expression", which is just an expression of sets and operations
# on those sets, and return a set of hosts that match the expression.
#
# e.g. parse("(xc | apollo) & slurm") will return a set of all hostnames that
# run slurm and are either xc or apollo systems.
def parse_qualities_expr(expr: str) -> set:
    hosts_data = yaml.safe_load(open(files.data() + "/hosts.yaml", "r"))
    schema = hosts_data["SCHEMA"]
    del hosts_data["SCHEMA"]

    chosen_hosts = set()

    sets = get_qualities_sets(schema, hosts_data)

    # build locals dict for eval
    locals = {hostname : hosts for hostname, hosts in sets.items()}

    # eval set expression
    # this is *relatively* safe, but not foolproof. if this ever gets connected
    # to the internet, change this.
    try:
        chosen_hosts = eval(expr, {"__builtins__" : None}, locals)
    except Exception as e:
        log.error(f"Failed to evaluate hosts: \"{expr}\". Make sure every quality is recognized (check with -L).")
        return set()

    return chosen_hosts

# Print a list of qualities available to use in parse_qualities_expr expressions
# and some examples of said expressions
def list_qualities() -> None:
    hosts_data = yaml.safe_load(open(files.data() + "/hosts.yaml", "r"))
    schema = hosts_data["SCHEMA"]

    # print nice table

    # find longest quality
    qsets = get_qualities_sets(schema, hosts_data)
    longest_len = max([len(k) for k in qsets.keys()]);

    # generate header
    log.info(f"{'QUALITY' + ' ' * (longest_len + 2 - len('QUALITY'))}EXAMPLE HOSTS")

    for q, hosts in qsets.items():
        sample = random.sample(hosts, min(2, len(hosts)));

        sample_str = ""
        for s in sample:
            sample_str += f"{s}, "
        if sample_str:
            sample_str = sample_str[:-2]

        log.info(f"{q + ' ' * (longest_len + 2 - len(q))}{sample_str if sample_str else '[]'}{'...' if len(hosts) > 2 else ''}")

    # generate some QUALEXPR examples
    log.info("")
    eg_wlms = random.sample(schema["wlm"], 2)
    eg_type = random.sample(schema["type"], 2)
    eg_os   = random.sample(schema["os"], 2)
    eval_str = f"({eg_wlms[0]} & ({eg_type[0]} | {eg_type[1]}))"
    result = parse_qualities_expr(eval_str)

    log.info(f"QUALEXPR example: \"{eval_str}\"")
    log.info(f"-> {result if result else '[]'}")
    log.info("")

    # shasta uans example
    eval_str = "(shasta13 | shasta15) & uan"
    result = parse_qualities_expr(eval_str)
    log.info(f"QUALEXPR example: \"{eval_str}\"")
    log.info(f"-> {result if result else '[]'}")
    log.info("")

    # one more for good measure
    eval_str = f"({eg_wlms[1]} & {eg_type[1]}) - {eg_os[0]}"
    result = parse_qualities_expr(eval_str)

    log.info(f"QUALEXPR example: \"{eval_str}\"")
    log.info(f"-> {result if result else '[]'}")
    log.info("")
    log.info("Run with -L again for more examples. Run with -l and -q QUALEXPR to evaluate a QUALEXPR and exit.")
    log.info("")

# Print a list of products that the test tool is known to be compatible with and
# some examples of PRODUCT:BRANCH strings that are used in -i, -t, and -b args
def list_products() -> None:
    prod_data = yaml.safe_load(open(files.data() + "/products.yaml", "r"))
    products = prod_data["products"]
    del products["SCHEMA"]
    branches = prod_data["branches"]
    branches_eg = prod_data["branches_examples"]

    log.info("Known products:")
    log.indent()
    for product in products:
        log.info(f"{product}")
    log.outdent()
    log.info("")

    log.info("Known branches:")
    log.indent()
    for branch in branches:
        log.info(f"{branch}")
    log.outdent()
    log.info("")

    log.info("Create arguments to --install, --tests, and --bundle in the form of PRODUCT:BRANCH")
    log.info("")

    # create some examples
    max_samples = max(len(products), len(branches_eg))
    psample = random.sample(products.keys(), len(products.keys()))
    bsample = random.sample(branches_eg, len(branches))

    log.info("e.g.")
    for i in range(max_samples):
        log.info(f"-i {psample[i % len(psample)]}:{bsample[i % len(bsample)]}")

# test logging's ability to print in color
def color_test() -> None:
    log.error("ERROR")
    log.warn("WARNING")
    log.info("INFO")
    os.environ[env.DEBUG] = "1"
    log.debug("DEBUG")

# read ./logs and print a summary in a format appropriate for slack
def print_slack_message() -> None:
    class Results():
        def __init__(self):
            self.total_passed = 0
            self.total_failed = 0
            self.total_skipped = 0

    # SKIP tests.py:Misc...
    # FAIL tests.py:Misc...
    #      tests.py:Misc...
    result_line_re = re.compile(r"^(     |SKIP |FAIL ).*$")

    # pegasus ------...
    host_line_re = re.compile(r"^(.*) -+$")

    hostname = None
    results = {}

    print("```")

    # read summary.txt
    with open("./logs/summary.txt", "r") as summ:
        for line in summ.readlines():
            line = line.rstrip()

            if host_line_re.match(line):
                hostname = host_line_re.match(line).group(1)
                results[hostname] = Results()
                continue

            if result_line_re.match(line):
                res = result_line_re.match(line).group(1)
                if res == "     ": # 5 spaces
                    # pass
                    results[hostname].total_passed += 1
                elif res == "SKIP ":
                    results[hostname].total_skipped += 1
                elif res == "FAIL ":
                    results[hostname].total_failed += 1
                continue

            if line.startswith("!!!"):
                print(line)

    longest_hostname_length = 0
    for host, _ in results.items():
        longest_hostname_length = max(longest_hostname_length, len(host))

    print()

    for host, res in results.items():
        total = res.total_passed + res.total_failed + res.total_skipped
        print("{0:{1}}: {2:3} passed, {3:3} failed, {4:3} skipped out of {5:3}".format(host, longest_hostname_length + 1, res.total_passed, res.total_failed, res.total_skipped, total))

    print("```")


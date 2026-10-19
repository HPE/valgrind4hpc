# Copyright 2021 Hewlett Packard Enterprise Development LP
#
# Connect to artifactory and download things

import os, platform, requests, subprocess

import cdst_test.log as log

BASE_URL = "http://arti.hpc.amslabs.hpecorp.net/artifactory"
TIMEOUT = 3

# given a "branch" (either "master", "release-latest", "release-xx.yy",
# "feature/PE-XXXXX", or "bugfix/PE-XXXXX", or "predev/PR-XXX"), and a product
# name (e.g. gdb4hpc, atp, cray-cti), return the urls to the latest product and
# tests rpm that live in the repository corresponding to branch.
# Returns None, None on error.
def get_latest_rpm_url(product: str, branch: str, repo_path: str = None) -> tuple:
    # where should we look in artifactory for the rpms?
    if not repo_path:
        repo_path = get_arti_repo(branch)

    if repo_path is None:
        log.error(f"Malformed branch name: {branch}")
        return None, None

    log.debug(f"determined repo path: {repo_path}")

    # what files are available there?
    # These come back sorted with the newest files listed first
    product_rpms, tests_rpms = get_available_product_rpms(repo_path, product)

    # pick newest
    latest_product = product_rpms[0] if product_rpms else None
    latest_tests   = tests_rpms[0] if tests_rpms else None

    # return urls
    return f"{BASE_URL}/{repo_path}/{latest_product}", \
           f"{BASE_URL}/{repo_path}/{latest_tests}"

# given a "branch" (either "master", "release-latest", "release-xx.yy",
# "feature/PE-XXXXX", "bugfix/PE-XXXXX", or "predev/PR-XXX"), determine where
# the appropriate rpms live in artifactory.
# Returns None on error.
def get_arti_repo(branch: str, folder: str = None) -> str:
    if not folder:
        folder = detect_os_arti_folder()

    if folder is None:
        log.error("Couldn't figure out arti folder.")
        return None

    arch = platform.uname()[5] # processor field
    if arch != "aarch64" and arch != "x86_64":
        log.debug(f"Unknown arch: {arch}")
        return None

    repo_path = None

    if branch == "master":
        repo_path = "pe-base-rpm-master-local/dev/master/" + folder + "/" + arch
    elif branch.startswith("release-"):
        branch = branch.replace("release-", "")
        if not branch == "latest":
            # explicit version passed
            repo_path = f"pe-base-rpm-stable-local/release/pe-{branch}/{folder}/{arch}"
        else:
            # "latest" passed

            # get a list of all available releases matching xx.yy
            directories = get_files_at("pe-base-rpm-stable-local/release/", folder=True, grep="pe-")

            if not directories:
                return None

            def release_key(folder):
                # extract the xx.yy portion of the folder with the form "/pe-xx.yy"
                num_part = folder[4:]
                major, minor = num_part.split(".")
                major = int(major) * 100
                minor = int(minor)
                return major + minor

            # find latest
            directories.sort(key=release_key, reverse=True)
            directory = directories[0] # has a leading /

            repo_path = f"pe-base-rpm-stable-local/release{directory}/{folder}/{arch}"
    elif branch.startswith("feature/")\
      or branch.startswith("bugfix/")\
      or branch.startswith("predev/"):
        typ = branch.split("/")[0]
        jira = branch.split("/")[1]
        if not jira:
            log.error(f"Empty branch name in \"{branch}\"")
            return None
        repo_path = f"pe-base-rpm-unstable-local/{typ}/{jira}/{folder}/{arch}"
    else:
        log.error(f"Bad branch string: {branch}")
        return None

    if not repo_path:
        return None

    # verify that it exists
    url = f"{BASE_URL}/{repo_path}/"
    log.info(f"Verifying {url}...")
    try:
        r = requests.get(url, timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        log.error(f"Request to {url} timed out")
        return None

    if r.status_code != 200:
        log.error(f"{url} doesn't exist.")
        return None

    return repo_path

# returns a tuple of lists of rpms filenames available at *repo_path* with filenames
# starting with *product*. The first list in the tuple is the list of product
# rpms, and the second is the list of tests rpms. The returned lists are sorted
# with the newest rpms listed first.
def get_available_product_rpms(repo_path: str, product: str) -> tuple:
    filenames = get_files_at(repo_path, folder=False, grep=product)

    # separate product rpm from -tests rpm
    log.debug(f"all filenames: {filenames}")
    product_rpms = [filename for filename in filenames if not "-tests" in filename]
    tests_rpms   = [filename for filename in filenames
        if "-tests" in filename and not "-dst-tests" in filename]

    # sort by date
    def date_in_filename(filename):
        # look for YYYYMMDDHHMMSS string in title
        for i in range(0, len(filename) - 14):
            if sum([c.isnumeric() for c in filename[i:i+14]]) < 14: continue
            # no non-numeric found
            return int(filename[i:i+14])

        log.error(f"Couldn't find date number in {filename}")
        # will throw TypeError
        return None

    try:
        product_rpms.sort(key=date_in_filename, reverse=True)
        tests_rpms.sort(key=date_in_filename, reverse=True)
    except TypeError:
        log.error("Failed to sort rpms")
        [], []

    log.debug(f"all products: {product_rpms}")
    log.debug(f"all tests: {tests_rpms}")

    return product_rpms, tests_rpms

# based on our OS, determine which folder in arti we'll download from.
# Returns None on error.
def detect_os_arti_folder() -> str:
    if not os.path.isfile("/etc/os-release"):
        return None

    folder = None
    vars_dict = {}

    arch = platform.uname()[5] # processor field
    if arch != "aarch64" and arch != "x86_64":
        log.debug(f"Unknown arch: {arch}")
        return None

    with open("/etc/os-release", "r") as releasefile:
        for line in releasefile.readlines():
            line = line.rstrip()
            if not line: continue # ignore empty lines

            key_value = line.split("=")
            # remove quotes from value
            vars_dict[key_value[0]] = key_value[1][1:-1]

    if "ID" not in vars_dict:
        return None
    if "VERSION" not in vars_dict:
        return None

    if vars_dict["ID"] == "sles":
        folder = "sle15_"
    elif vars_dict["ID"] == "rhel":
        folder = "rhel_"
    else:
        return None

    if folder == "sle15_":
        vers = vars_dict["VERSION"][3:].lower()
        folder += vers
    elif folder == "rhel_":
        vers = vars_dict["VERSION"].split(' ')[0].replace(".", "_")
        folder += vers
    else:
        return None

    folder += "_pe"

    return folder

def get_files_at(repo_path: str, folder: bool, grep: str):
    # make sure path ends with /
    if not repo_path.endswith("/"): repo_path += "/"

    url = f"{BASE_URL}/api/storage/{repo_path}"
    try:
        r = requests.get(url, timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        log.error(f"Request to {url} timed out")
        return None

    if r.status_code != 200:
        log.error(f"bad request to {url}")
        return None

    data = r.json()
    if not grep:
        return [child["uri"] for child in data["children"] if child["folder"] == folder]
    else:
        return [child["uri"] for child in data["children"] if child["folder"] == folder and child["uri"].startswith("/" + grep)]

# Download *filename* from *repo_path* and save it in *dst*.
# Returns True on success and False on failure.
def download_file(url: str, dest_dir: str) -> bool:
    filename = os.path.basename(url)

    if not os.path.isdir(dest_dir):
        log.error(f"Specify a directory (not a file) to save {url} in.")
        return False

    try:
        r = requests.get(url, timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        log.error(f"Request to {url} timed out")
        return None

    if r.status_code != 200:
        return False
    with open(f"{dest_dir}/{filename}", "wb") as f:
        f.write(r.content)

    log.info(f"Downloaded: {filename}")

    return True

# Returns true if the BASE_URL is resolvable
def test_artifactory_visibility() -> bool:
    try:
        r = requests.get(BASE_URL, timeout=TIMEOUT)
        return r.status_code == 200
    except requests.exceptions.Timeout:
        return False

def get_local_rpm_version(path) -> str:
    # pull out version
    p = subprocess.run(["rpm", "-q", "--qf", "%{NAME}", path], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if not p.stdout:
        return None

    # above command produces "product-1.2.3.4"
    version = p.stdout.decode()
    version = version[version.rfind("-") + 1:]
    return version

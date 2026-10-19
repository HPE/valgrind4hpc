from avocado import Test

import os, sys, socket, yaml, time

# should match LIB_DIR in cdst_test/env.py
if os.getenv("CDST_TESTS_LIB_DIR"):
    sys.path.append(os.getenv("CDST_TESTS_LIB_DIR"))
else:
    print("Can't find CDST_TESTS_LIB_DIR")
    exit(-1)

import cdst_test.useful as useful
class Useful(Test):
    def test_detect_wlm(self):
        self.assertTrue(useful.detect_wlm() != None, "Couldn't detect WLM")

    def test_getout(self):
        path = useful.getOut(self, "getout")
        self.assertTrue(path == "./tmp/getout.out", "got " + path)

    def test_gettxt(self):
        path = useful.getTxt(self, "gettxt")
        self.assertTrue(path == os.getcwd() + "/tests.py.data/gettxt.txt", "got " + path)

    def test_test_presence_of_binary(self):
        error = useful.test_presence_of_binary("./hello_mpi")
        self.assertTrue(error == None, error)

import cdst_test.textcheck as textcheck
class TextCheck(Test):
    def run_test_compare(self, name):
        getOut = useful.getOut
        getTxt = useful.getTxt
        result, error = textcheck.compare_files(getTxt(self, name), getOut(self, name))
        self.assertTrue(result, error)

    def run_test_compare_fail(self, name):
        getOut = useful.getOut
        getTxt = useful.getTxt
        result, error = textcheck.compare_files(getTxt(self, name), getOut(self, name))
        self.assertFalse(result, "compare_files returned true, but it shouldn't have")
        self.assertTrue(error != "")

    def test_buildqueue(self):
        q = textcheck.build_section_queue(useful.getTxt(self, "buildqueue"))

        classes = [
            textcheck.SingleLineSection,
            textcheck.SingleLineSection,
            textcheck.CommentSection,
            textcheck.WildcardSection,
            textcheck.UnorderedSection,
            textcheck.IgnoreSection,
        ]

        self.assertTrue(len(q) == len(classes), "Queue length is wrong: %s vs %s" % (len(q), len(classes)))

        for i in range(len(classes)):
            qc = q[i].__class__
            cc = classes[i]
            self.assertTrue(qc == cc, qc.__name__ + " is not " + cc.__name__)

    def test_makeregex(self):
        r = textcheck.make_regex("%.*[abc]%word")
        self.assertTrue(r"^.*[abc]word$" == r, "got " + r)

    def test_comparelines(self):
        cl = textcheck.compare_lines

        self.assertTrue(cl("hello", "hello"))
        self.assertFalse(cl("hello", "goodbye"))
        self.assertTrue(cl("hello", "hello  "))
        self.assertTrue(cl(r"%hello.*%", "hello world"))
        self.assertFalse(cl(r"%hello.*%", "goodbye world"))

    def test_singleline(self):
        blob = "This is one line\n"
        section = textcheck.SingleLineSection(blob)

        self.assertTrue(section.feed_line("This is one line"))
        self.assertFalse(section.feed_line("This is one (bad) line"))

    def test_unordered(self):
        blob = ("%<\n"
                "one line\n"
                "two line\n"
                "%-\n"
                "three line\n"
                "four line\n"
                "%>\n")
        section = textcheck.UnorderedSection(blob)

        section.feed_line("one line")
        section.feed_line("three line")
        section.feed_line("two line")
        section.feed_line("four line")

        self.assertTrue(section.satisfied)

        blob = ("%<\n"
                "one line\n"
                "two line\n"
                "%-\n"
                "three line\n"
                "four line\n"
                "%>\n")
        section = textcheck.UnorderedSection(blob)

        self.assertFalse(section.feed_line("two line"))
        self.assertFalse(section.feed_line("four line"))
        section.feed_line("one line")
        section.feed_line("three line")

        self.assertFalse(section.satisfied)

    def test_wildcard(self):
        blob = "%*"
        linesection = textcheck.SingleLineSection("Endline")
        section = textcheck.WildcardSection(blob)
        section.next_section = linesection

        self.assertTrue(section.feed_line("no match") == None)
        self.assertTrue(section.feed_line("no match 2") == None)
        self.assertTrue(section.feed_line("Endline"))

    def test_comment(self):
        blob = r"%# hello, a comment"
        linesection = textcheck.SingleLineSection("Endline")
        section = textcheck.CommentSection(blob)
        section.next_section = linesection

        self.assertTrue(section.feed_line("no match"))
        self.assertTrue(section.feed_line("no match 2"))
        self.assertTrue(section.feed_line("Endline"))

    def test_ignore(self):
        blob = ("%[\n"
                "%prefix1\.\.\..*%\n"
                "%prefix2\.\.\..*%\n"
                "%]\n")
        section = textcheck.IgnoreSection(blob)

        self.assertTrue(section.feed_line("prefix1... hello!"))
        self.assertFalse(section.feed_line("pay attention!"))
        self.assertTrue(section.feed_line("prefix2... hello!"))

    def test_compare_1(self):
        self.run_test_compare("compare_1")

    def test_compare_2(self):
        self.run_test_compare("compare_2")

    def test_compare_3(self):
        self.run_test_compare("compare_3")

    def test_compare_4(self):
        self.run_test_compare_fail("compare_4")

    def test_compare_5(self):
        self.run_test_compare("compare_5")

    def test_compare_6(self):
        self.run_test_compare("compare_6")

    def test_compare_7(self):
        self.run_test_compare("compare_7")

    def test_compare_8(self):
        self.run_test_compare("compare_8")

    def test_compare_9(self):
        self.run_test_compare_fail("compare_9")

import cdst_test.modules as modules
class Modules(Test):
    def setUp(self):
        self.dry_run_tests = {
                "load __invalid__module__name": False,
                "list": True,
                "__invalid__command__": False
            }

    def test_dry_run(self):
        for command, result in self.dry_run_tests.items():
            self.assertTrue(
                modules.dry_run(*command.split()) == result,
                "module " + command + " returned " + str(result))

    def test_module_test_force_unreliable(self):
        # simulate an environment where the return code of the module command
        # is unreliable. on a system where this really is the case, it's a
        # duplicate of the test above.
        modules.MODULE_SHELL_RETURNCODE_RELIABLE = False

        for command, desired_result in self.dry_run_tests.items():
            returned = modules.dry_run(*command.split())
            self.assertTrue(
                returned == desired_result,
                "module " + command + " returned " + str(returned))

    def test_invoke_successfully(self):
        # unfortunately, it's not really possible to silence the output of this...
        self.assertTrue(modules.invoke_successfully("list"), "module list returned False.")
        self.assertFalse(modules.invoke_successfully("__invalid__"), "Failed to detect that \"module __invalid__\" would fail.")

    def test_capture_output(self):
        # tmod: "Currently Loaded Modulefiles:"
        # lmod: "Currently Loaded Modules:"
        self.assertTrue("Currently Loaded Module" in modules.capture_output("list"),
            "Module capture output got something it didn't expect.")

    def test_shell_returncode_reliable(self):
        # this test is more informational in nature than it is testing critical
        # functionality.
        #
        # it tests if MODULE_SHELL_RETURNCODE_RELIABLE (determined in modules.py)
        # returned True. If not, things like dry_run() have to resort to
        # more hacky methods of determining module command success/failure.
        #
        # so, it is okay for this test to fail if the test_dry_run pass still
        # passes. If *both* fail, that is a problem.
        if not modules.MODULE_SHELL_RETURNCODE_RELIABLE:
            self.log.warn("The module command's shell return code is not reliable. If test_dry_run passed, this is a nonissue. If it failed, something needs to be fixed.")

import cdst_test.config as config
import yaml
class Config(Test):
    def test_valid_yaml(self):
        # ensure that Node.generate_yaml generates valid yaml
        cfg = config.load_config("test_tool_config.yaml")
        try:
            y = yaml.safe_load(cfg.generate_yaml())
        except Exception as e:
            self.fail(f"Failed to load yaml ({e})")

    def test_valid_patch(self):
        # ensure that the default config gets patched properly
        cfg = config.load_config("test_tool_config.yaml")
        magic = cfg.get("launch/args/extra")
        if magic != "try to find me!":
            self.fail("Didn't find magic token")

class Misc(Test):
    def test_wait_for_five_seconds(self):
        # for testing progress bar UI of remote testing tool
        time.sleep(5)

    def test_always_skip(self):
        # used to test the remote testing tool's ability to detect skips
        self.cancel("This test is always skipped.")

    def test_sometimes_skip(self):
        if self.params.get("skip_some"):
            self.cancel("Skip parameter enabled")

    def test_skip_from_env(self):
        # test that CDST_TESTS_SKIPS is filled by test_tool
        if os.getenv("CDST_TESTS_SKIPS") == "skip_from_env":
            self.cancel("I was told by CDST_TESTS_SKIP to skip")
        self.fail("I should have skipped")

    def test_always_fail(self):
        # used to test the remote testing tool's ability to detect a test
        # that failed across the board
        self.fail("This test always fails!")

    # the fail_if_x tests are used to test the remote testing tool's ability
    # to detect that a certain test failed on systems that share a common quality

    def get_host(self):
        hosts_data = yaml.safe_load(open(self.get_data("hosts.yaml", must_exist = True), "r"))
        hostname = os.getenv("CDST_TESTS_WHEREAMI") if os.getenv("CDST_TESTS_WHEREAMI") else socket.gethostname()
        print(f"get_host: I think I'm on {hostname}")
        return hosts_data[hostname] if hostname in hosts_data else None

    def test_fail_if_xc(self):
        host = self.get_host()
        if host and host["type"] == "xc":
            self.fail("Always fails on xc systems")

    def test_fail_if_apollo(self):
        host = self.get_host()
        if host and host["type"] == "apollo":
            self.fail("Always fails on apollo systems")

    def test_fail_if_cs(self):
        host = self.get_host()
        if host and host["type"] == "cs":
            self.fail("Always fails on cs systems")

    def test_fail_if_everest(self):
        host = self.get_host()
        if host and host["type"] == "everest":
            self.fail("Always fails on everest systems")

    def test_fail_if_shasta(self):
        host = self.get_host()
        if host and host["type"].startswith("shasta"):
            self.fail("Always fails on shasta systems")

    def test_fail_if_slurm(self):
        if useful.detect_wlm() == "SLURM": self.fail("Always fail if slurm")

    def test_fail_if_alps(self):
        if useful.detect_wlm() == "ALPS": self.fail("Always fail if ALPS")

    def test_fail_if_pals(self):
        if useful.detect_wlm() == "PALS": self.fail("Always fail if PALS")

    def test_fail_if_ssh(self):
        if useful.detect_wlm() == "SSH": self.fail("Always fail if SSH")

    def test_fail_if_x86(self):
        host = self.get_host()
        if host and host["arch"] == "x86":
            self.fail("Always fails on x86 systems")

    def test_fail_if_aarch(self):
        host = self.get_host()
        if host and host["arch"] == "aarch":
            self.fail("Always fails on aarch systems")

import cdst_test.artifactory as arti
class Artifactory(Test):
    def test_arti_visibility(self):
        self.assertTrue(arti.test_artifactory_visibility() == True, "artifactory not found")

    def test_get_latest_rpm_url_master(self):
        product_urls, test_urls = arti.get_latest_rpm_url("cray-cti", "master")
        self.assertTrue(len(product_urls) != 0, "Failed to find master product rpms for cray-cti")
        self.assertTrue(len(test_urls) != 0, "Failed to find master test rpms for cray-cti")

    def test_get_latest_rpm_url_latest_release(self):
        product_urls, test_urls = arti.get_latest_rpm_url("cray-cti", "release-latest")
        self.assertTrue(len(product_urls) != 0, "Failed to find master product rpms for cray-cti")
        self.assertTrue(len(test_urls) != 0, "Failed to find master test rpms for cray-cti")

    def test_get_arti_repo(self):
        self.assertTrue(arti.get_arti_repo("master") is not None, "Failed to get master repo path")
        self.assertTrue(arti.get_arti_repo("release-latest") is not None, "Failed to get master repo path")


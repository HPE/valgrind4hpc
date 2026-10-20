#!/usr/bin/env python3

import sys, os, subprocess, signal, time

import avocado
from avocado import Test
from avocado.utils import process as avproc

try:
    # try cwd first
    from cdst_test import textcheck
except ModuleNotFoundError:
    # fall back to ./cdst-test
    sys.path.insert(0, os.getcwd() + "/cdst-test")
    from cdst_test import textcheck

# Raised when there is an unexpected error that should end the test. Exception should
# bubble up to the top testing function where the test should be ended via .end_test
class EndTestError(Exception):
    def __init__(self, cancel_reason=None, fail_reason=None):
        self.cancel_reason = cancel_reason
        self.fail_reason = fail_reason or "Unspecified failure"

    def end_test(self, test):
        if self.cancel_reason is not None:
            test.cancel(self.cancel_reason)
        else:
            test.fail(self.fail_reason)

def create_outfile(testname):
    try:
        os.mkdir("./tmp")
    except FileExistsError as e:
        pass

    return f"./tmp/{testname}.out"

# Kill p and all of its descendants
def kill_popen(p):
    if p is not None and p.poll() != 0:
        descs = avproc.kill_process_tree(p.pid, signal.SIGTERM)
        time.sleep(3)
        for pid in descs:
            avproc.safe_kill(pid, signal.SIGKILL)

def run_valgrind4hpc(test: Test, testname: str, launch):
    outfile = create_outfile(testname)
    seconds_passed = 0
    timeout_seconds = 120

    out = b""

    try:
        # explicitly set to None in case Popen raises an exception. the finally: block
        # needs p to be defined before it references it.
        p = None
        p = subprocess.Popen(launch,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )

        while seconds_passed < timeout_seconds:
            try:
                # raises TimeoutExpired on timeout. if communicate retruns, the process exited.
                out_chunk, _ = p.communicate(timeout=5)
                out += out_chunk
                break
            except subprocess.TimeoutExpired as e:
                seconds_passed += 5

        if seconds_passed >= timeout_seconds:
            raise EndTestError(cancel_reason="Timeout")

        return p.returncode
    finally:
        # clean up process and log output
        if p is not None and p.poll() == None:
            # kill and read last data chunk
            kill_popen(p)
            out_chunk, _ = p.communicate()
            out += out_chunk

        with open(outfile, "wb") as of:
            of.write(out)

def check_output(test : Test, testname: str, reffile: str):
    txt = test.get_data(reffile, must_exist = True)
    return textcheck.compare_files(txt, f"./tmp/{testname}.out")

def default_launch_argv(test, testname, binary):
    args = ["valgrind4hpc", "-n", "2"]
    addtional_args = os.getenv("CDST_TESTS_LAUNCHER_ARGS")
    if addtional_args is not None:
        args += ["--launcher-args=" + addtional_args]
    args += [binary]
    return args

def verify_binary(test, binary):
    if not os.path.exists(binary):
        test.cancel(f"Missing binary: {binary}")
    return binary

def make_leak_txt(test, testname, binary):
    if not os.path.exists(f"{binary}.c"):
        test.cancel(f"Missing source file: {binary}.c")

    with open(f"{binary}.c", "r") as cfile:
        # find "// LEAK"
        leak_linenum = None
        leak_func = None
        for i, line in enumerate(cfile.readlines()):
            if "// LEAK" in line:
                leak_linenum = str(i + 1) # enumerate starts at 0
                # assume there's only one memory function on the line
                if "malloc" in line:
                    leak_func = "malloc"
                elif "calloc" in line:
                    leak_func = "calloc"
                elif "realloc" in line:
                    leak_func = "realloc"
                break

        if leak_linenum == None or leak_func == None:
            test.cancel(f"Could not find \"// LEAK\" in {binary}.c")

    output = ""
    with open("./tests.py.data/leak.txt.template", "r") as temp:
        for line in temp.readlines():
            outline = line
            outline = outline.replace("__fn__", leak_func)
            outline = outline.replace("__filename__", binary.replace("./src/", ""))
            outline = outline.replace("__linenum__", leak_linenum)
            output += outline

    with open(f"./tests.py.data/{testname}.txt", "w") as txtfile:
        txtfile.write(output)

def run_test(test, testname, launch_argv, expected_exit_code, expected_txt):
    try:
        # run and check
        r = run_valgrind4hpc(test, testname, launch_argv)
        test.assertTrue(
            r == expected_exit_code,
            f"valgrind4hpc exit code mismatch (got {r}, expected {expected_exit_code})"
        )
        test.assertTrue(*check_output(test, testname, expected_txt))
    except EndTestError as ete:
        if ete.cancel_reason is not None and ete.cancel_reason == "Timeout":
            with open(f"./tmp/{testname}.out", "r") as of:
                if "Passed Init" not in of.read():
                    test.cancel("Timed out before launch")
                else:
                    test.fail("Timed out after launch")

        ete.end_test(test)

class Valgrind4hpc(Test):
    def test_nonexistent_binary(self):
        testname = "nonexistent_binary"
        binary = "./src/nonexistent" # this doesn't exist
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 1, "nonexistent.txt")

    def test_mpi_sanity(self):
        testname = "mpi_sanity"
        binary = verify_binary(self, "./src/mpi_sanity_check")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "any_summary.txt")

    def test_mpi_no_error(self):
        testname = "mpi_no_error"
        binary = verify_binary(self, "./src/mpi_no_error")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "no_error.txt")

    def test_shmem_sanity(self):
        testname = "shmem_sanity"
        binary = verify_binary(self, "./src/shmem_sanity_check")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "any_summary.txt")

    def test_shmem_no_error(self):
        testname = "shmem_no_error"
        binary = verify_binary(self, "./src/shmem_no_error")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "no_error.txt")

    def test_mpi_illegal_free_after_malloc(self):
        testname = "mpi_illegal_free_malloc"
        binary = verify_binary(self, "./src/mpi_illegal_free_malloc")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "illegal_free.txt")

    def test_mpi_illegal_free_after_calloc(self):
        testname = "mpi_illegal_free_calloc"
        binary = verify_binary(self, "./src/mpi_illegal_free_calloc")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "illegal_free.txt")

    def test_mpi_illegal_free_after_realloc_grow(self):
        testname = "mpi_illegal_free_realloc_grow"
        binary = verify_binary(self, "./src/mpi_illegal_free_realloc_grow")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "illegal_free.txt")

    def test_mpi_illegal_free_after_realloc_shrink(self):
        testname = "mpi_illegal_free_realloc_shrink"
        binary = verify_binary(self, "./src/mpi_illegal_free_realloc_shrink")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "illegal_free.txt")

    def test_mpi_illegal_free_on_stack(self):
        testname = "mpi_illegal_free_stack"
        binary = verify_binary(self, "./src/mpi_illegal_free_stack")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "illegal_free.txt")

    def test_mpi_mem_leak_after_malloc(self):
        testname = "mpi_mem_leak_malloc"
        binary = verify_binary(self, "./src/mpi_mem_leak_malloc")
        make_leak_txt(self, testname, binary)
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, f"{testname}.txt")

    def test_mpi_mem_leak_after_calloc(self):
        testname = "mpi_mem_leak_calloc"
        binary = verify_binary(self, "./src/mpi_mem_leak_calloc")
        make_leak_txt(self, testname, binary)
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, f"{testname}.txt")

    def test_mpi_mem_leak_after_realloc_grow(self):
        testname = "mpi_mem_leak_realloc_grow"
        binary = verify_binary(self, "./src/mpi_mem_leak_realloc_grow")
        make_leak_txt(self, testname, binary)
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, f"{testname}.txt")

    def test_mpi_mem_leak_after_realloc_shrink(self):
        testname = "mpi_mem_leak_realloc_shrink"
        binary = verify_binary(self, "./src/mpi_mem_leak_realloc_shrink")
        make_leak_txt(self, testname, binary)
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, f"{testname}.txt")

    def test_mpi_oob_read_after_malloc(self):
        testname = "mpi_oob_read_malloc"
        binary = verify_binary(self, "./src/mpi_oob_read_malloc")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "oob_read.txt")

    def test_mpi_oob_read_after_calloc(self):
        testname = "mpi_oob_read_calloc"
        binary = verify_binary(self, "./src/mpi_oob_read_calloc")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "oob_read.txt")

    def test_mpi_oob_read_after_realloc_grow(self):
        testname = "mpi_oob_read_realloc_grow"
        binary = verify_binary(self, "./src/mpi_oob_read_realloc_grow")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "oob_read.txt")

    def test_mpi_oob_read_after_realloc_shrink(self):
        testname = "mpi_oob_read_realloc_shrink"
        binary = verify_binary(self, "./src/mpi_oob_read_realloc_shrink")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "oob_read.txt")

    def test_mpi_oob_mpi_read(self):
        testname = "mpi_oob_read_mpi"
        binary = verify_binary(self, "./src/mpi_oob_read_mpi")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "oob_read.txt")

    def test_mpi_oob_write_after_malloc(self):
        testname = "mpi_oob_write_malloc"
        binary = verify_binary(self, "./src/mpi_oob_write_malloc")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "oob_write.txt")

    def test_mpi_oob_write_after_calloc(self):
        testname = "mpi_oob_write_calloc"
        binary = verify_binary(self, "./src/mpi_oob_write_calloc")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "oob_write.txt")

    def test_mpi_oob_write_after_realloc_grow(self):
        testname = "mpi_oob_write_realloc_grow"
        binary = verify_binary(self, "./src/mpi_oob_write_realloc_grow")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "oob_write.txt")

    def test_mpi_oob_write_after_realloc_shrink(self):
        testname = "mpi_oob_write_realloc_shrink"
        binary = verify_binary(self, "./src/mpi_oob_write_realloc_shrink")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "oob_write.txt")

    def test_mpi_oob_mpi_write(self):
        testname = "mpi_oob_write_mpi"
        binary = verify_binary(self, "./src/mpi_oob_write_mpi")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "oob_write.txt")

    @avocado.skip("Shmem errors undetected until PE-38232 is done")
    def test_shmem_double_free(self):
        testname = "shmem_double_free"
        binary = verify_binary(self, "./src/shmem_double_free")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "illegal_free.txt")

    @avocado.skip("Shmem errors undetected until PE-38232 is done")
    def test_shmem_oob_read(self):
        testname = "shmem_oob_read"
        binary = verify_binary(self, "./src/shmem_oob_read")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "oob_read.txt")

    @avocado.skip("Shmem errors undetected until PE-38232 is done")
    def test_shmem_oob_write(self):
        testname = "shmem_oob_write"
        binary = verify_binary(self, "./src/shmem_oob_write")
        launch = default_launch_argv(self, testname, binary)
        run_test(self, testname, launch, 0, "oob_write.txt")

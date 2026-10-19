# Copyright 2020 Hewlett Packard Enterprise Development LP
#
# functional testing helper functions

import subprocess
import os
import sys
import re
import time
import threading
from . import log
from . import files

# try to detect a WLM
#
# returns a string or None
def detect_wlm():
    # this is done in a subprocess so that we can do things like "source $CRAY_ENABLE_PE".
    # some machines need that to be done before slurm binaries become visible.
    # XXX: for some machines you *have* to invoke it via bash -c source for it to work
    argv = ["/bin/bash", "-c", "source " + files.scripts() + "/detect_wlm.sh"]
    p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    if p.returncode == 0:
        return p.stdout.decode().strip()
    else:
        # couldn't find anything
        # re-launch for logs
        successful_launch(argv, quiet=True)
        return None

def successful_launch(launch_array, quiet = False):
    log.debug("Running " + " ".join(launch_array))
    if not quiet:
        rc = subprocess.run(launch_array, stdout=sys.stdout, stderr=sys.stderr).returncode
        log.debug(f"Returned {rc}\n")
        return rc == 0
    else:
        p = subprocess.run(launch_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log.debug(f"returncode was: {p.returncode}\n")
        log.debug(f"stdout was:\n{p.stdout.decode()}\n")
        log.debug(f"stderr was:\n{p.stderr.decode()}\n")
        return p.returncode == 0

def launch_until(test, test_name, launch_array, env_dict = None, until_seen = None, immediate_success_on_match = False):
    if env_dict:
        for key, value in env_dict.items():
            os.environ[key] = str(value)

    kill_seconds = 3

    test.log.debug("Launching: %s", " ".join(launch_array))
    if until_seen:
        test.log.debug("Process will be killed %s seconds after matching \"%s\"" % (kill_seconds, until_seen))

    p = subprocess.Popen(launch_array, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    if not p.pid:
        test.error("Failed to launch program: " + " ".join(launch_array))

    killed = False

    with open(getOut(test, test_name), "w") as outfile:
        for byteline in iter(p.stdout.readline, b''):
            line = byteline.decode("utf-8")
            test.log.debug(line.rstrip())
            outfile.write(line)

            if until_seen and not killed:
                m = re.search(until_seen, line)

                if m:
                    test.log.debug("Killing program after matching %s" % until_seen)
                    killed = True

                    if immediate_success_on_match == True:
                        test.log.debug("Immediate success on match is True, killing now.")
                        p.kill()
                        break
                    else:
                        test.log.debug("Immediate success on match is False, killing in %s seconds." % kill_seconds)
                        # the goal here is to see something that marks the end of the
                        # output we're looking for, give the program some time to
                        # output the rest of the data, then manually kill it so we
                        # don't have to wait 60+ seconds on some systems for srun et al
                        # to kill it for us
                        threading.Thread(target=kill_pid_in, args=(p, kill_seconds)).start()

        if not killed:
            p.wait()

        test.log.debug("%s exited with %s" % (" ".join(launch_array), p.returncode))
        return p.returncode

def kill_pid_in(process : subprocess.Popen, seconds):
    time.sleep(seconds)
    if process.poll() == None:
        print("Killing pid: " + str(process.pid))
        process.kill()
    else:
        print("Not killing pid %s: already exited." % str(process.pid))

def getTxt(test, name: str):
    filename = name + ".txt"
    path = test.get_data(filename, must_exist = True)
    if not path:
        test.error("Couldn't get txt file: " + str(filename))
    return path

def getOut(test, name: str):
    return "./tmp/" + name + ".out"

def test_presence_of_binary(bin):
    if not os.path.isfile(bin):
        return "%s doesn't exist." % bin
    if not os.access(bin, os.X_OK):
        return "%s isn't executable" % bin
    return None

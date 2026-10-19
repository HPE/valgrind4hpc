# Copyright 2021 Hewlett Packard Enterprise Development LP
#
# Logging functionality for the testing tool

import os, sys, threading

import cdst_test.env as env

_LOG_THREAD_LOCAL = threading.local()

class Logger():
    # Escape codes to produce colored text
    colormap = {
        -1 : "\033[0m", # no color
        1 : "\033[91m", # error
        2 : "\033[93m", # warning
        3 : "\033[0m",  # info
        4 : "\u001b[30;1m" # debug
    }

    def __init__(self, file) -> None:
        self.file = file # log fd, can also be stdout/stderr
        self.hook = None # log hook function. Called after every log item, if defined
        self.lock = threading.Lock() # required to output log messages
        self.tee  = False # when logging to a file, display messages on the terminal too?
        self.idt = 0   # indent messages by this much when printing to a tty

    def set_hook(self, fn):
        self.hook = fn

    def close(self):
        if self.file:
            self.file.close()

    def _log(self, string : str, level : int):
        if self.file is None:
            print("Log with no log file", file=sys.stderr)
            return

        def print_with_color(string, level):
            color = Logger.colormap[level]
            nocolor = Logger.colormap[-1]

            if os.getenv(env.LOG_NO_COLOR) is not None:
                color = ""
                nocolor = ""

            print(f"{'- ' * self.idt }{color}{string}{nocolor}", file=sys.stderr)

        with self.lock:
            if level <= 3 or os.getenv(env.DEBUG):
                if self.file.isatty():
                    print_with_color(string, level)
                else:
                    # no colors
                    prefixmap = {
                        1 : "ERROR    ",
                        2 : "WARNING  ",
                        3 : "INFO     ",
                        4 : "DEBUG    "
                    }
                    prefix = prefixmap[level]
                    print(f"{prefix}: {string}", file=self.file)
                    self.file.flush()
                    if self.tee:
                        print_with_color(string, level)

        if self.hook is not None:
            self.hook(string, level)

    def debug(self, string : str):
        self._log(string, 4)

    def info(self, string : str):
        self._log(string, 3)

    def warn(self, string : str):
        self._log(string, 2)

    def error(self, string : str):
        self._log(string, 1)

    def indent(self):
        self.idt += 1

    def outdent(self):
        self.idt = max(0, self.idt - 1)

def _get_thread_local_logger() -> Logger:
    log = getattr(_LOG_THREAD_LOCAL, "log", None)
    if not log:
        _LOG_THREAD_LOCAL.log = Logger(sys.stderr)
        log = _LOG_THREAD_LOCAL.log
    return log

def set_hook(fn):
    _get_thread_local_logger().set_hook(fn)

def close():
    _get_thread_local_logger().close()

# debug only shows up on the user's terminal if CDST_TESTS_DEBUG is set

def debug(string : str):
    _get_thread_local_logger().debug(string)

# info, warn, and error always show up on the user's terminal.

def info(string : str):
    _get_thread_local_logger().info(string)

def warn(string : str):
    _get_thread_local_logger().warn(string)

def error(string : str):
    _get_thread_local_logger().error(string)

def indent():
    _get_thread_local_logger().indent()

def outdent():
    _get_thread_local_logger().outdent()

def get_log_dir():
    directory = os.getenv(env.LOG_DIR)
    if not directory: directory = "./logs"
    return directory

def new_log_file(filename, tee=False):
    directory = get_log_dir()

    try:
        os.mkdir(directory)
    except FileExistsError:
        pass
    except PermissionError:
        print(f"warning: can't create {directory} (permission denied), log messages won't be saved.", file=sys.stderr)
        return Logger(sys.stderr)

    try:
        # deduce filename
        filename = directory + "/" + filename
        # overwrite filename if env var is present. useful for setting before
        # spawning child processes that don't know about the parent process
        if os.getenv(env.LOG_FILE_NAME):
            filename = directory + "/" + os.getenv(env.LOG_FILE_NAME)

        # open file
        try:
            f = open(filename, "a")
        except PermissionError:
            print(f"warning: can't open {filename} (permission denied), log messages won't be saved", file=sys.stderr)
            return Logger(sys.stderr)

        # configure
        l = Logger(f)
        l.tee = tee # print to terminal in addition to file?
        return l
    except IOError as e:
        print(f"warning: failed to open log file {filename} ({e})", file=sys.stderr)

    # above logic should return early, or fall through to here if something went wrong.
    l = Logger(sys.stderr)
    l.tee = tee
    return l

_LOG_THREAD_LOCAL.log = new_log_file(f"test_tool.log", tee=True)

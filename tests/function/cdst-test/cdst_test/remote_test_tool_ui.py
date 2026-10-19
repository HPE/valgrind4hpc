# Copyright 2021 Hewlett Packard Enterprise Development LP
#
# Display test results to the user

import sys, os

import cdst_test.env as env

class BarUI():
    # progress bar display

    def __init__(self, all_test_contexts) -> None:
        self.ctxs = all_test_contexts
        self.wheel = 0
        self.padding = 0

    def prepare(self) -> None:
        # make some room for the bars
        print("\n") # + automatic newline from python's print function

        self.padding = 0

        for ctx in self.ctxs:
            self.padding = max(self.padding, len(ctx.ssh.get_friendly_name()) + 1)
            print()

    def display(self) -> None:
        def num_threads_alive():
            return len([tr for tr in self.ctxs if tr.thread and tr.thread.is_alive()])

        # uses terminal escape codes to move the print cursor around

        # move back up to top of display
        print(f"\u001b[{len(self.ctxs) + 1}A", end="")

        print(f"\033[2K{num_threads_alive()} out of {len(self.ctxs)} tasks still running:")
        for ctx in self.ctxs:
            status = None
            if ctx.state == ctx.STATE_consume_results:
                status = self.get_progress_bar(ctx)
            elif ctx.state == ctx.STATE_finish_up:
                status = self.get_progress_bar(ctx) + " " + ctx.get_status_str()
            else:
                status = ctx.get_status_str()

            header = "  " + ctx.ssh.get_friendly_name() + (" " * (self.padding - len(ctx.ssh.get_friendly_name()))) + ": "

            print(f"\033[2K{header}{status}")

    def finish(self) -> None:
        pass

    def get_progress_bar(self, ctx):
        txt = ""
        if ctx.tty_mode:
            txt = "▐"
            for i, t in enumerate(ctx.results):
                txt += self.generate_char(t, wheel = i == ctx.results_collected)
            txt += "▌ "
        txt += f"({ctx.results_collected}/{len(ctx.results)})"

        return txt

    def generate_char(self, result, wheel = False):
        green = "\u001b[32m"
        yellow = "\u001b[33m"
        red = "\u001b[1m\u001b[31m"
        nocolor = "\u001b[0m"

        if wheel:
            self.wheel += 1
            wheelstr = "▁▂▃▄▅▆▇"
            return wheelstr[(self.wheel // 3) % len(wheelstr)]

        if result.result == result.RESULT_ok:
            return f"{green}▆{nocolor}"
        elif result.result == result.RESULT_skipped:
            return f"{yellow}▆{nocolor}"
        elif result.result == result.RESULT_failed:
            return f"{red}!{nocolor}"
        elif result.result == result.RESULT_unknown:
            return " "
        else:
            return "?"

class LogUI():
    # messy but complete display of every log message. meant for dumping into a
    # file instead of human eyes.

    def __init__(self, all_test_contexts) -> None:
        self.ctxs = all_test_contexts
        self.last_status = {}

    def prepare(self) -> None:
        print("Note: This output may be incomplete. See system-specific logs for compete logs.")

        for ctx in self.ctxs:
            ctx.tty_mode = False

        self.last_status = {}

    def display(self) -> None:
        for tr in self.ctxs:
            this_status = tr.ui_status
            if tr.ssh.get_friendly_name() not in self.last_status or this_status != self.last_status[tr.ssh.get_friendly_name()]:
                self.last_status[tr.ssh.get_friendly_name()] = this_status
                print(f"{tr.ssh.get_friendly_name()}: {this_status}")
        sys.stdout.flush()

    def finish(self) -> None:
        pass

def get_default_ui(all_test_contexts: list):
    if os.getenv(env.DEBUG):
        return LogUI(all_test_contexts)

    if sys.stdout.isatty():
        return BarUI(all_test_contexts)
    return LogUI(all_test_contexts)

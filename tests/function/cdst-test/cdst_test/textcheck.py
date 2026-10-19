# Copyright 2020 Hewlett Packard Enterprise Development LP
#
# match ".txt" or "ref" files with ".out" files with markup features


import re
import os

def make_regex(line):
    # break the line into characters
    chars = [char for char in line]
    reChars =['^']

    # regular expression for literals that need to be escaped in the re
    spchars = re.compile(r"[.^$*+?{}\\[\]|()]")
    inRe = False
    for c in chars:
        if inRe:
            if c == '%':
                c = ''
                inRe = False
        elif c == '%':
            c = ''
            inRe = True
        elif spchars.match(c):
            c = "\\" + c
        elif c == '\n':
            c = "\\n"
        elif c == '\t':
            c = "\\t"
        reChars.append(c)
    reChars.append('$')

    # put back together into a string
    reLine = ''.join(reChars)
    return reLine

def compare_lines(ref_line, out_line):
    ref_line = ref_line.rstrip()
    out_line = out_line.rstrip()

    # fill in run time variables
    substitutions = {
        r"%%testdir%%" : lambda: os.getcwd()
    }

    for key, sub in substitutions.items():
        ref_line = ref_line.replace(key, sub())

    # create regex
    percents = ref_line.count('%')
    if percents != 0 and percents & 1 == 0:
        return re.match(make_regex(ref_line), out_line) != None
    else:
        return ref_line == out_line

class SingleLineSection:
    def __init__(self, blob = None):
        self.satisfied = False
        self.re = re.compile(r"^.*\n?")
        self.priority = 10

        self.line_to_match = None

        if blob:
            self.build_from_blob(blob)

    def build_from_blob(self, blob):
        assert(len(blob.splitlines()) == 1)
        self.line_to_match = blob.splitlines()[0]

    def feed_line(self, line):
        assert(self.line_to_match != None)
        if compare_lines(self.line_to_match, line):
            self.satisfied = True
            return True
        return False

    def get_starting_lines(self):
        return [self.line_to_match]

class UnorderedSection:
    def __init__(self, blob = None):
        self.satisfied = False
        self.re = re.compile(r"^%<\n.*?^%>\n?", re.MULTILINE | re.DOTALL)
        self.priority = 0

        self.expected_queues = []

        if blob:
            self.build_from_blob(blob)

    def build_from_blob(self, blob):
        assert(self.re.match(blob) != None)
        queue = []
        for line in blob.splitlines():
            if re.match(r"^(%<|%-|%>)", line):
                if len(queue) != 0:
                    self.expected_queues.append(queue)
                queue = []
            else:
                queue.append(line)

        print(self.expected_queues)

        assert(len(self.expected_queues) > 0)

    def feed_line(self, line):
        matched = False
        for q in self.expected_queues:
            if compare_lines(q[0], line):
                q.pop(0)
                if len(q) == 0:
                    self.expected_queues.remove([])
                matched = True
                break
        if not matched:
            return False

        if len(self.expected_queues) == 0:
            self.satisfied = True
            return True

        return None

    def get_starting_lines(self):
        return [q[0] for q in self.expected_queues]

class WildcardSection:
    def __init__(self, blob = None):
        self.satisfied = False
        self.re = re.compile(r"^%\*.*\n?")
        self.priority = 9

        self.next_section = None

        if blob:
            self.build_from_blob(blob)

    def build_from_blob(self, blob):
        pass

    def feed_line(self, line):
        # eat lines until we find one that matches next section
        if self.next_section != None:
            for l in self.next_section.get_starting_lines():
                if compare_lines(l, line):
                    self.satisfied = True
                    return True

        return None

    def get_starting_lines(self):
        return self.next_section.get_starting_lines()

class RepeatedLineSection:
    def __init__(self, blob = None):
        self.satisfied = False
        self.re = re.compile(r"^%\+ (.*)\n?")
        self.priority = 7
        self.next_section = None

        if blob:
            self.build_from_blob(blob)

    def build_from_blob(self, blob):
        mat = self.re.match(blob)
        assert(mat is not None)
        self.line = mat.group(1)

    def feed_line(self, line):
        # eat lines that match our string until we find one that matches next section
        if compare_lines(self.line, line):
            # ok, wait for next line
            return None
        else:
            # mismatch, is it the beginning of the next line?
            if self.next_section != None:
                for l in self.next_section.get_starting_lines():
                    if compare_lines(l, line):
                        self.satisfied = True
                        return True
        # didn't match anything
        return False

    def get_starting_lines(self):
        return [self.line]

class IgnoreSection:
    def __init__(self, blob = None):
        self.satisfied = False
        self.re = re.compile(r"^%\[\n.*?^%\]\n?", re.MULTILINE | re.DOTALL)
        self.priority = 8

        self.next_section = None
        self.ignores = []

        if blob:
            self.build_from_blob(blob)

    def build_from_blob(self, blob):
        assert(self.re.match(blob) != None)
        self.ignores = blob.splitlines()[1:-1]

    def feed_line(self, line):
        for ig in self.ignores:
            print(ig + " vs " + line)
            if compare_lines(ig, line) == True:
                return True
        return False

    def get_starting_lines(self):
        return self.next_section.get_starting_lines()

class CommentSection:
    def __init__(self, blob = None):
        self.satisfied = False
        self.re = re.compile(r"^%#.*\n?")
        self.priority = 1

        self.next_section = None

        if blob:
            self.build_from_blob(blob)

    def build_from_blob(self, blob):
        assert(self.re.match(blob) != None)

    def feed_line(self, line):
        return True

    def get_starting_lines(self):
        return self.next_section.get_starting_lines()

def build_section_queue(ref_file_path):
    possible_sections = [
        SingleLineSection(),
        UnorderedSection(),
        WildcardSection(),
        IgnoreSection(),
        CommentSection(),
        RepeatedLineSection(),
    ]

    # sort by priority (lower priority will be tried first)
    possible_sections.sort(key=lambda section: section.priority)

    sections = []

    ref_text_blob = open(ref_file_path, "r").read()
    while ref_text_blob != "":
        matched = False
        for ps in possible_sections:
            match = ps.re.match(ref_text_blob)
            if match:
                blob = match.group(0)

                if len(sections) != 0:
                    last_section = sections[len(sections) - 1]
                else:
                    last_section = None

                sections.append(ps.__class__(blob))

                if last_section and \
                    (last_section.__class__ == WildcardSection \
                    or last_section.__class__ == CommentSection \
                    or last_section.__class__ == IgnoreSection \
                    or last_section.__class__ == RepeatedLineSection):
                    last_section.next_section = sections[len(sections) - 1]

                ref_text_blob = ref_text_blob.replace(blob, "", 1)

                matched = True
                break
        if not matched:
            return None

    return sections

def compare_files(ref_file_path, out_file_path):
    sections = build_section_queue(ref_file_path)

    with open(out_file_path, "r") as of:
        lines = of.readlines()
        idx = 0
        ignore_sections = []
        while idx < len(lines):
            line = lines[idx]

            # check if we should ignore the line
            ignored = False
            for ignore_section in ignore_sections:
                if ignore_section.feed_line(line):
                    # ignore this line
                    idx += 1
                    ignored = True
                    break
            if ignored:
                continue

            # check if we've used up all of our sections
            if len(sections) == 0:
                return False, "Out file has more than expected"

            # pick up any new ignore sections
            if sections[0].__class__ == IgnoreSection:
                ignore_sections.append(sections[0])
                sections.pop(0)
                continue

            # see if the line satisfies the current markup section
            satisfied = sections[0].feed_line(line.rstrip())
            if satisfied == True:
                if sections[0].__class__ != WildcardSection \
                    and sections[0].__class__ != CommentSection:
                    idx += 1
                sections.pop(0)
            elif satisfied == False:
                return False, ("%s:%s: Expecting \"%s\", got \"%s\"." %
                    (out_file_path, idx + 1, str(sections[0].get_starting_lines()), line))
            else:
                # satisfied == None which indicates "inconclusive". just continue on
                idx += 1

    # special case: it's ok to end with a single wildcard/comment/repeat left in the queue
    if len(sections) != 0 and not (len(sections) == 1 \
            and (sections[0].__class__ == WildcardSection \
            or sections[0].__class__ == CommentSection \
            or sections[0].__class__ == RepeatedLineSection)):
        error = "%s: Never found \"%s\"" % (out_file_path, str(sections[0].get_starting_lines()))
        print(error)
        return False, error

    return True, ""

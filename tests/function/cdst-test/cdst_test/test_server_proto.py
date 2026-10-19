# Copyright 2021-2023 Hewlett Packard Enterprise Development LP
#
# Description of data passed between remote test client and server

import enum, socket, threading

from socket import timeout as SocketTimeout

import cdst_test.log as log

# TODO: Remove this?
MAX_REQUEST_LEN = 1024 * 100

class CommandType(enum.Enum):
    ACK = enum.auto()
    DATA = enum.auto()
    QUIT = enum.auto()
    CHDIR = enum.auto()
    YAML_PATH = enum.auto()
    ERROR = enum.auto()
    DO_SETUP_ENV = enum.auto()
    DO_SANITY_CHECKS = enum.auto()
    DO_BUILD = enum.auto()
    DO_TESTS = enum.auto()
    DO_CLEAN = enum.auto()
    TASK_FINISHED = enum.auto()
    GET_MODULES_FLAVOR = enum.auto()
    MODULE_LOAD = enum.auto()
    MODULE_USE = enum.auto()
    TEST_ARTI_CONNECTION = enum.auto()
    GET_ARTI_OS = enum.auto()
    DOWNLOAD_RPM = enum.auto()
    INSTALL_LOCAL_RPM = enum.auto()

class Command():
    # A command type and some data

    # messages tend to get sent/received in long chunks of concatenated messages,
    # so these are the message start and message end markers. while the logic for
    # this might be a little flawed (collisions are technically possible), in
    # practice it gets the job done. and it's an excuse to use fun ascii characters!
    start = "¶+Ø"
    end = "¤¬¾"

    def __init__(self, command_type : CommandType, extra_data : str = "") -> None:
        self.command_type = command_type
        self.data = extra_data

    def encode(self) -> bytes:
        return (self.start + str(self.command_type.value) + " " + self.data + self.end).encode()

    def __str__(self) -> str:
        return f"{self.command_type} {self.data}"

# Convert bytes into a Command object
def command_from_bytes(data : bytes) -> Command:
    decoded = data.decode().replace(Command.start, "", 1).replace(Command.end, "", 1)
    split = decoded.split(" ")

    t = int(split[0])
    d = ""
    if len(split) > 1:
        d = " ".join(split[1:])
    r = None

    try:
        r = CommandType(t)
    except ValueError as e:
        log.warn(f"{t} isn't a valid command type({e}).")
        raise ValueError()

    return Command(r, d)

# Take a chunk of data as received by recv and split it into a list of Command
# objects. If the chunk of data has anything leftover that is too short to create
# a full command, return it in overflow.
def extract_commands_from_chunk(data : bytes) -> tuple:
    str = data.decode()
    commands = []
    overflow = ""

    while str:
        if str.startswith(Command.start) and Command.end in str:
            end = str.find(Command.end) + len(Command.end)
            commands.append(str[:end].encode())
            str = str[end:]
            overflow = str.encode()
        else:
            overflow = str.encode()
            str = ""

    return commands, overflow

# Send a command to the test server on the other end of *socket* and wait in a loop
# until it sends back TASK_FINISHED. Return the piece of data returned with the
# TASK_FINISHED message.
def send_task_and_wait(socket : socket.socket, comm : Command, early_exit_flag: threading.Event) -> str:
    ret = None
    log.debug(f"Sending request: {comm.encode()}")

    socket.settimeout(180)
    socket.sendall(comm.encode())

    done = False
    overflow = b''

    while not done and not early_exit_flag.is_set():
        log.debug("Waiting for message from server...")
        try:
            chunk = socket.recv(MAX_REQUEST_LEN)
        except SocketTimeout as e:
            log.error(f"Timed out waiting for message from server. ({e})")
            ret = None
            break

        if chunk == b'':
            log.error("Received blank results from server.")
            ret = None
            break

        datalist, overflow = extract_commands_from_chunk(overflow + chunk)
        log.debug(f"got commands: {datalist}")

        for datum in datalist:
            comm = command_from_bytes(datum)
            if comm.command_type == CommandType.DATA:
                log.info(f"{comm.data}")
            elif comm.command_type == CommandType.TASK_FINISHED:
                log.debug(f"Done: {comm}")
                ret = comm.data
                done = True
            elif comm.command_type == CommandType.ACK:
                log.debug("Got ACK")
            else:
                log.error(f"Unhandled: {comm}")
                ret = None
                done = True

    # If we exit early, report result as failure so calling function stops issuing
    # any more commands
    if early_exit_flag.is_set():
        log.debug("Early exit")
        ret = None

    socket.settimeout(None)
    return ret

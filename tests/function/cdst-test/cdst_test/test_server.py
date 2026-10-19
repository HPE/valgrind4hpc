# Copyright 2021 Hewlett Packard Enterprise Development LP
#
# Spawn a server and run test functions on command

import socket, functools, os, getpass, sys

import cdst_test.log as log
import cdst_test.ssh as ssh
import cdst_test.test_server_commands as scmds
import cdst_test.job_environment as jenv
import cdst_test.env as env

from cdst_test.test_server_proto import CommandType, Command, MAX_REQUEST_LEN, command_from_bytes

def send_response(comm: Command, conn : socket.socket):
    response = comm.encode()

    if len(response) > MAX_REQUEST_LEN:
        log.error(f"Message was too big to send!")
        send_response(CommandType.ERROR, {})
        return

    conn.sendall(response)

# Hook for log module. Any time something is logged, send it to the client as data.
def send_log_message(conn : socket.socket, string, level):
    if level < 4:
        conn.settimeout(0.5)
        send_response(Command(CommandType.DATA, string), conn)
        conn.settimeout(None)

def main(args):
    if args.log_mode:
        # redirect all output to a file
        sys.stdout = log._get_thread_local_logger().file
        sys.stderr = log._get_thread_local_logger().file
        log._get_thread_local_logger().tee = False

    if os.getenv(env.CHDIR):
        os.chdir(os.getenv(env.CHDIR))
        log.info(f"Changed cwd to {os.getcwd()}")

    # set root for later file lookups
    os.environ[env.SERVER_ROOT] = os.getcwd()

    # start listening on port
    if not args.server_port:
        log.error("No port passed to server")
        return False
    port = int(args.server_port)

    # on some systems that require a qsub to do anything, the qsub sends you off
    # to another machine. The client doesn't know where we get sent off to, so
    # if we detect that we've moved, lay a ssh tunnel behind us so the client
    # can eventually find us.

    old_host = os.getenv(env.UNALLOCED_HOSTNAME)
    if old_host and socket.gethostname() != old_host:
        log.warn(f"Detected a hostname change after allocation ({old_host} -> {socket.gethostname()}), laying ssh tunnel")
        args = ["ssh", "-R", f"{port}:localhost:{port}", f"{getpass.getuser()}@{old_host}", "-Nn"]
        with ssh.LongRunningSubprocess(args, False) as tunnel:
            start_server(port)
            tunnel.kill()
            return True

    start_server(port)

    log.close()
    return True

def start_server(port):
    for r in CommandType:
        log.info(f"{r.value}: {r}")

    with socket.socket() as s:
        # so that when the client sends DO_SETUP_ENV, we can
        # quickly restart the server on the same port without issues.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        s.bind(('', port))
        log.info(f"Waiting on port {port}...")
        s.listen()
        s.settimeout(45)
        conn, addr = s.accept()
        s.settimeout(None)
        log.info(f"Connected by {addr}")
        with conn:
            listen_for_commands(s, conn)

def listen_for_commands(sock, conn):
    log_hook = functools.partial(send_log_message, conn)
    keep_going = True
    yaml = None

    while keep_going:
        log.info("Waiting...")
        data = conn.recv(MAX_REQUEST_LEN)
        if not data: break

        comm = command_from_bytes(data)

        if comm:
            log.info(f"Got {comm}")
            send_response(Command(CommandType.ACK), conn)
            log.set_hook(log_hook)

            if comm.command_type == CommandType.ACK:
                pass
            elif comm.command_type == CommandType.DO_SETUP_ENV:
                # on success, this function doesn't return. it only returns on error!
                err = scmds.do_setup_env(yaml, comm, sock, conn)
                send_response(err, conn) # send error to client, wait for quit message
            elif comm.command_type == CommandType.DO_SANITY_CHECKS:
                send_response(scmds.do_sanity_checks(yaml, comm), conn)
            elif comm.command_type == CommandType.DO_BUILD:
                send_response(scmds.do_build(yaml, comm), conn)
            elif comm.command_type == CommandType.DO_TESTS:
                send_response(scmds.do_tests(yaml, comm), conn)
            elif comm.command_type == CommandType.DO_CLEAN:
                send_response(scmds.do_clean(yaml, comm), conn)
            elif comm.command_type == CommandType.TEST_ARTI_CONNECTION:
                send_response(scmds.do_test_arti_connection(yaml, comm), conn)
            elif comm.command_type == CommandType.GET_ARTI_OS:
                send_response(scmds.do_get_arti_os(yaml, comm), conn)
            elif comm.command_type == CommandType.DOWNLOAD_RPM:
                send_response(scmds.do_download_rpm(yaml, comm), conn)
            elif comm.command_type == CommandType.INSTALL_LOCAL_RPM:
                send_response(scmds.do_install_local_rpm(yaml, comm), conn)
            elif comm.command_type == CommandType.MODULE_LOAD:
                send_response(scmds.do_module_load(yaml, comm), conn)
            elif comm.command_type == CommandType.MODULE_USE:
                send_response(scmds.do_module_use(yaml, comm), conn)
            elif comm.command_type == CommandType.GET_MODULES_FLAVOR:
                send_response(scmds.do_get_module_flavor(), conn)
            elif comm.command_type == CommandType.CHDIR:
                send_response(scmds.do_chdir(yaml, comm), conn)
            elif comm.command_type == CommandType.YAML_PATH:
                yaml = os.path.expanduser(comm.data)
                log.info(f"Set yaml path to {yaml}")
                send_response(Command(CommandType.TASK_FINISHED, "ok"), conn)
            elif comm.command_type == CommandType.QUIT:
                send_response(scmds.do_quit(yaml, comm), conn)
                keep_going = False
                conn.close()
                log.set_hook(None)
                log.info("Connection closed")
            else:
                log.error(f"Unhandled request: {comm.command_type}.")
                send_response(Command(CommandType.ERROR), conn)

            log.set_hook(None)
        else:
            break

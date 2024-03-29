/******************************************************************************\
 * valgrind4hpc_starter.C - Application starter portion of parallel valgrind tool.
 *
 * Copyright 2015-2023 Hewlett Packard Enterprise Development LP.
 *
 * Unpublished Proprietary Information.
 * This unpublished work is protected to trade secret, copyright and other laws.
 * Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
 * no part of this work or its content may be used, reproduced or disclosed
 * in any form.
 *
 ******************************************************************************/

#include <cerrno>
#include <cstring>

#include <iostream>
#include <fstream>
#include <sstream>

#include <future>

#include <string>
#include <vector>
#include <tuple>

#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <signal.h>
#include <dlfcn.h>

#include "ArgvDefs.hpp"
#include "utils/MsgQueue.hpp"

#include "valgrind4hpc_defs.h"

std::ofstream dbg_stream;
//#define DEBUG(str, x) do { str << x; } while (0)
#define DEBUG(str, x)

// Activate PALS startup barrier manually through libpals
static void run_pals_barrier()
{
	// Function prototypes
	int (*pals_init2)(void **state);
	int (*pals_fini)(void *state);
	int (*pals_start_barrier)(void *state);

	// Open libpals
	DEBUG(dbg_stream, "opening libpals from ld_cache" << std::endl);
	auto libpals_handle = std::unique_ptr<void, int (*)(void*)>
		{::dlopen("libpals.so", RTLD_LAZY), ::dlclose};
	if (!libpals_handle) {
		throw std::runtime_error("dlopen libpals failed: " + std::string{dlerror()});
	}

	auto dlsym_func = [](void* handle, char const* name) {
		auto result = ::dlsym(handle, name);
		if (auto error = ::dlerror()) {
			throw std::runtime_error("dlsym " + std::string{name} + " failed: " + error);
		}
		return result;
	};

	// Open functions
	*(void**)(&pals_init2) = dlsym_func(libpals_handle.get(), "pals_init2");
	*(void**)(&pals_fini) = dlsym_func(libpals_handle.get(), "pals_fini");
	*(void**)(&pals_start_barrier) = dlsym_func(libpals_handle.get(), "pals_start_barrier");

	// Call barrier initialization
	DEBUG(dbg_stream, "calling libpals barrier initialization" << std::endl);
	void *state;
	pals_init2(&state);
	pals_start_barrier(state);
	pals_fini(state);
}

int
main(int argc, char** argv)
{
	// parse the starter arguments
	bool palsBarrier = false;
	int queueKey = -1;
	std::string xmlSocket, binPath, valgrindPath, tmpDir;
	std::string targetBinary, valgrindTool;
	std::vector<std::string> binaryArgsToAdd, valgrindArgsToAdd, suppressionsToAdd;

	{ using SA = StarterArgv;
		IncomingArgv<SA> parsedArgv(argc, argv);

		int c; std::string value;
		while (true) {
			std::tie(c, value) = parsedArgv.get_next();
			if (c <= 0) { break; }

			switch (c) {

			case SA::PalsBarrier.val:
				palsBarrier = true;
				break;

			case SA::QueueKey.val:
				queueKey = std::stoi(value);
				break;

			case SA::ValgrindTool.val:
				valgrindTool = value;
				break;

			case SA::Suppressions.val:
				suppressionsToAdd.emplace_back(value);
				break;

			case SA::ValgrindArg.val:
				valgrindArgsToAdd.emplace_back(value);
				break;
			case SA::Binary.val:
				targetBinary = value;
				break;

			case SA::BinaryArg.val:
				binaryArgsToAdd.emplace_back(value);
				break;

			case '?':
			default:
				throw std::runtime_error("bad arg");
			}
		}
	}

	// Call PALS startup barrier if needed
	if (palsBarrier) {
		try {
			run_pals_barrier();
		} catch (std::exception const& ex) {
			DEBUG(dbg_stream, "warning: " << ex.what() << " (ignore if not on PALS system)" << std::endl);
		}
	}

	// Receive socket information from message queue
	{ MsgQueue msgQueue(queueKey);
		using MsgType = MsgQueue::MsgType;
		if (msgQueue.recv(xmlSocket, MsgType::SocketInfo) < 0) {
			throw std::runtime_error("msgrcv SocketInfo failed");
		}
		if (msgQueue.recv(binPath, MsgType::BinPath) < 0) {
			throw std::runtime_error("msgrcv BinPath failed");
		}
		if (msgQueue.recv(tmpDir, MsgType::TmpDir) < 0) {
			throw std::runtime_error("msgrcv TmpDir failed");
		}
		valgrindPath = binPath + "/valgrind";
	}

	DEBUG(dbg_stream, "xmlSocket: '" << xmlSocket << "'" << std::endl);
	DEBUG(dbg_stream, "binPath: '" << binPath << "'" << std::endl);

	// check required arguments
	if (xmlSocket.empty() || binPath.empty()) {
		throw std::runtime_error("missing arg");
	}

	// construct valgrind arguments
	using VA = ValgrindArgv;
	OutgoingArgv<VA> valgrindArgv(valgrindPath);

	// constant valgrind arguments
	valgrindArgv.add(VA::TraceChildren);
	valgrindArgv.add(VA::XMLMode);
	valgrindArgv.add(VA::SilenceChildAfterFork);

	// add valgrind tool argument
	if (!valgrindTool.empty()) {
		valgrindArgv.add(VA::Tool, valgrindTool);
	}

	// add xml socket argument
	valgrindArgv.add(VA::XMLSocket, xmlSocket);

	// user custom valgrind args
	for (const auto& arg : valgrindArgsToAdd) {
		valgrindArgv.add(VA::Argument(arg));
	}

	// add suppressions
	for (const auto& supp : suppressionsToAdd) {
		valgrindArgv.add(VA::Suppressions, binPath + "/../" + supp);
	}

	// add binary and arguments
	valgrindArgv.add(VA::Argument(targetBinary));
	for (const auto& binArg : binaryArgsToAdd) {
		valgrindArgv.add(VA::Argument(binArg));
	}

	//fork off the valgrind/application process
	pid_t valgrind_pid = fork();
	if (valgrind_pid < 0)
	{
		throw std::runtime_error(("fork() failed: " + std::string(std::strerror(errno))).c_str());
	}

	// child case - this is the app
	if (valgrind_pid == 0)
	{
		// Disable subprocess barrier if in PALS mode
	        ::setenv("PALS_STARTUP_BARRIER", "0", 1);

		// tell valgrind about the location of its libraries
		if(setenv("VALGRIND_LIB", (binPath + "/../lib").c_str(), 1) != 0) {
			throw std::runtime_error("Failed to setenv VALGRIND_LIB");
		}

		{ struct stat buffer;
			const std::string wrapperPath(binPath + "/../lib/dmapp-wrap.so");
			// enable dmapp wrapper library if present
			if (stat(wrapperPath.c_str(), &buffer) == 0) {
				if(setenv("LD_PRELOAD", wrapperPath.c_str(), 1) != 0) {
					throw std::runtime_error("Failed to setenv LD_PRELOAD");
				}
			}
		}

		// disable debugging under ATP
		if(setenv("ATP_ENABLED", "0", 1) != 0) {
			throw std::runtime_error("Failed to setenv ATP_ENABLED");
		}

		// Set temporary directory to CTI storage, in case frontend's
		// TMPDIR is not accessible on backend
		setenv("TMPDIR", tmpDir.c_str(), 1);

		// exec
		char* const *valgrind_argv_ptr = valgrindArgv.get();
		execvp(valgrindPath.c_str(), valgrind_argv_ptr);

		// exec shouldn't return
		std::cerr << argv[0] << ": return from exec!" << std::endl;
		exit(1);
	}

	// launch thread to waitpid the valgrind child
	bool valgrindRunning = true;
	auto childFuture = std::async(std::launch::async, [&]() {
		int status;
		while (true) {
			// XXX: See PE-38960. MPI apps launched by CTI on
			// cfa6k don't get properly started and get stuck after a
			// SIGSTOP from somewhere. When that issue is fixed,
			// this whole while loop can be collapsed into a blocking
			// waitpid() call.
			sleep(1);
			auto pid = waitpid(valgrind_pid, &status, WNOHANG | WUNTRACED);
			if (pid == valgrind_pid && (WIFEXITED(status) || WIFSIGNALED(status))) {
				// valgrind has exited, stop waiting
				break;
			} else if (pid == valgrind_pid && WIFSTOPPED(status)) {
				// valgrind stopped for some reason. try to start it again
				kill(valgrind_pid, SIGCONT);
			}
		}
		valgrindRunning = false;
		return status;
	});

	// wait for shutdown message
	{ MsgQueue msgQueue(queueKey);
		using MsgType = MsgQueue::MsgType;

		std::string shutdownMessage;
		int recv = msgQueue.recv(shutdownMessage, MsgType::Shutdown);
		if (recv < 0) {
			if ((errno != EIDRM) && (recv != -1)) {
				throw std::runtime_error("Finish rcv failed");
			}
		}

		// does the backend want us to destroy the kernel queue
		if (!shutdownMessage.compare(MsgQueue::DestroyOnShutdown)) {
			msgQueue.deregister();
		}

		// if valgrind hasn't ended yet, kill it
		if (valgrindRunning) {
			kill(valgrind_pid, SIGKILL);
		}
	}

	// get valgrind status from future waitpid and return with it
	int status = childFuture.get();
	if (WIFEXITED(status)) {
		return WEXITSTATUS(status);
	}

	return 0;
}

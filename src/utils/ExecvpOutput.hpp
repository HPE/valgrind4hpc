/*********************************************************************************\
 * ExecvpOutput.hpp - fork / execvp a program and read its output as an istream
 *
 * Copyright 2014-2019,2020 Hewlett Packard Enterprise Development LP.
 *
 * Unpublished Proprietary Information.
 * This unpublished work is protected to trade secret, copyright and other laws.
 * Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
 * no part of this work or its content may be used, reproduced or disclosed
 * in any form.
 *
 *********************************************************************************/

#ifndef _EXECVPOUTPUT_HPP
#define _EXECVPOUTPUT_HPP

#include <unistd.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/types.h>

#include <boost/optional.hpp>

#include <sstream>
#include <streambuf>

#include "FdBuf.hpp"

/* Pipe - create and track closed ends of pipe */
class Pipe {
private:
	enum Ends { ReadEnd = 0, WriteEnd = 1 };
	bool readOpened = false;
	bool writeOpened = false;

	int fds[2];

public:
	static const int stdin = 0;
	static const int stdout = 1;
	static const int stderr = 2;

	Pipe(int flags = 0) {
		if (pipe2(fds, flags)) {
			throw std::runtime_error("Pipe error");
		}

		readOpened = true;
		writeOpened = true;
	}

	~Pipe() {
		if (readOpened) {
			close(fds[ReadEnd]);
		}

		if (writeOpened) {
			close(fds[WriteEnd]);
		}
	}

	void closeRead() {
		if (!readOpened) {
			throw "Already closed read end";
		}

		close(fds[ReadEnd]);
		readOpened = false;
	}

	void closeWrite() {
		if (!writeOpened) {
			throw "Already closed write end";
		}

		close(fds[WriteEnd]);
		writeOpened = false;
	}

	const int getReadFd() { return fds[ReadEnd]; }
	const int getWriteFd() { return fds[WriteEnd]; }
};

/* ExecvpOutput - fork / execvp a program and read its output as an istream */
class ExecvpOutput {

	class Line : std::string {
		friend std::istream& operator>>(std::istream& is, Line& line) {
			return std::getline(is, line);
		}
	};

	Pipe p;
	FdBuf pipeInBuf;
	std::istream pipein;
	pid_t child;

	using MaybeString = boost::optional<std::string>;

	static MaybeString optional_getline(std::istream &is, char delim = '\n') {
		std::string result;

		if (!std::getline(is, result, delim)) {
			return boost::none;
		}

		return MaybeString(result);
	}

public:
	ExecvpOutput(const char *binaryName, char* const* argv)
		: pipeInBuf(p.getReadFd())
		, pipein(&pipeInBuf)
		, child(fork())
	{

		if (child < 0) {
			throw std::runtime_error(std::string("fork() for ") + binaryName + " failed!");
		} else if (child == 0) { // child side of fork
			/* prepare the output pipe */
			p.closeRead();
			dup2(p.getWriteFd(), Pipe::stdout);
			dup2(p.getWriteFd(), Pipe::stderr);
			p.closeWrite();

			execvp(binaryName, argv);
			throw std::runtime_error(std::string("execvp() on ") + binaryName + " failed!");
		}

		/* create istream from output pipe */
		p.closeWrite();
	}

	int getExitStatus() {
		int status = 0;
		if ((waitpid(child, &status, 0) < 0) && (errno != ECHILD)) {
			throw std::runtime_error(
				std::string("waitpid() on ") + std::to_string(child) + " failed!");
		}
		return WEXITSTATUS(status);
	}

	MaybeString optional_getline() { return optional_getline(pipein); }
	std::istream& stream() { return pipein; }
};


#endif

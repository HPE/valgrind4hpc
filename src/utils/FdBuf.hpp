/******************************************************************************\
 * FdBuf.hpp - Streambuf from file descriptor
 *
 * Copyright 2015-2017,2020 Hewlett Packard Enterprise Development LP.
 *
 * Unpublished Proprietary Information.
 * This unpublished work is protected to trade secret, copyright and other laws.
 * Except as permitted by contract or express written permission of Hewlett Packard Enterprise Development LP.,
 * no part of this work or its content may be used, reproduced or disclosed
 * in any form.
 *
 ******************************************************************************/

#include <sstream>
#include <streambuf>
#include <fcntl.h>
#include <unistd.h>
#include <sys/types.h>
class FdBuf : public std::streambuf {
public:
	FdBuf(int fd_) : fd(fd_) {
		if (fd_ < 0) {
			throw std::invalid_argument("Invalid file descriptor");
		}
	}

	FdBuf() : fd(-1) {}

	FdBuf(FdBuf&& buf) : fd(buf.fd) {
		buf.fd = -1;
	}

	virtual ~FdBuf() {
		if (fd >= 0) {
			close(fd);
		}
	}

protected:
	virtual int underflow() {
		if (fd < 0) { throw std::runtime_error("File descriptor not set"); }

		ssize_t numBytesRead = read(fd, &readCh, 1);
		if (numBytesRead == 0) {
			return EOF;
		}

		setg(&readCh, &readCh, &readCh + 1);
		return static_cast<int>(readCh);
	}

	virtual int overflow(int writeCh) {
		if (fd < 0) { throw std::runtime_error("File descriptor not set"); }

		write(fd, &writeCh, 1);
		return writeCh;
	}

private:
	char readCh;
protected:
	int fd;
};
/******************************************************************************\
 * Copyright 2022 Hewlett Packard Enterprise Development LP.
******************************************************************************/

#pragma once

#include <config.h>

#include <stdlib.h>
#include <stdarg.h>
#include <stdio.h>
#include <unistd.h>
#include <limits.h>
#include <errno.h>
#include <sys/time.h>

#include <memory>

// Common logging functions

static inline int64_t
get_millisecond()
{
	struct timeval  tv;
	gettimeofday(&tv, NULL);
	return (tv.tv_sec) * 1000 + (tv.tv_usec) / 1000;
}

using FilePtr = std::unique_ptr<FILE, decltype(&::fclose)>;
namespace globals
{
	// Logging
	static const auto first_millisecond = get_millisecond();
	static auto logFile = FilePtr{nullptr, ::fclose};
};

static inline void
__attribute__((format(printf, 1, 2)))
log(const char *format, ...)
{
	if (globals::logFile == nullptr) {
		if (auto const logEnabled = getenv("CTI_DEBUG")) {
			if (auto const logDir = getenv("CTI_LOG_DIR")) {
				char hostname[PATH_MAX];
				::gethostname(hostname, PATH_MAX);
				hostname[PATH_MAX - 1] = '\0';

				char logPath[PATH_MAX + strlen(hostname)];
				sprintf(logPath, "%s/%s." COMPONENT_NAME ".%d.log", logDir, hostname, getpid());
				globals::logFile = FilePtr{::fopen(logPath, "w"), ::fclose};
			}
		}
	}

	if (globals::logFile != nullptr) {
		fprintf(globals::logFile.get(), "[%10ld] ", get_millisecond() - globals::first_millisecond);
		va_list argp;
		va_start(argp, format);
		vfprintf(globals::logFile.get(), format, argp);
		va_end(argp);
		fflush(globals::logFile.get());
	}
}
